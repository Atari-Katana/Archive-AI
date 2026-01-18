use candle_core::{Tensor, Result, DType};
use candle_nn::VarBuilder;

/// Weight-only quantized linear layer (FP8/INT8)
pub struct WeightOnlyLinear {
    qweight: Tensor,  // Quantized weights (INT8 or FP8)
    scales: Tensor,   // Dequantization scales
    bias: Option<Tensor>,
}

impl WeightOnlyLinear {
    pub fn new(qweight: Tensor, scales: Tensor, bias: Option<Tensor>, _bits: u8) -> Self {
        Self {
            qweight,
            scales,
            bias,
        }
    }

    pub fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let dequant_weight = (&self.qweight * &self.scales)?;
        let mut out = x.matmul(&dequant_weight)?;
        if let Some(bias) = &self.bias {
            out = out.broadcast_add(bias)?;
        }
        Ok(out)
    }
}

/// AWQ quantized linear layer with custom CUDA kernel
pub struct AWQLinear {
    qweight: Tensor,
    scales: Tensor,
    qzeros: Tensor,
    bias: Option<Tensor>,
}

impl AWQLinear {
    /// Load AWQ weights from safetensors
    pub fn load(vb_int: VarBuilder, vb_f16: VarBuilder, shape: (usize, usize)) -> Result<Self> {
        let (in_features, out_features) = shape;
        let group_size = 128;

        let qweight_raw = vb_int.get((in_features, out_features / 8), "qweight")?;
        let qweight = qweight_raw.to_dtype(DType::U32)?;
        
        let scales_raw = vb_f16.get((in_features / group_size, out_features), "scales")?;
        let scales = scales_raw.to_dtype(DType::F16)?;
        
        let qzeros_raw = vb_int.get((in_features / group_size, out_features / 8), "qzeros")?;
        let qzeros = qzeros_raw.to_dtype(DType::U32)?;
        
        let bias = if vb_f16.contains_tensor("bias") {
            Some(vb_f16.get(out_features, "bias")?)
        } else {
            None
        };

        Ok(Self {
            qweight,
            scales,
            qzeros,
            bias,
        })
    }

    pub fn forward(&self, x: &Tensor) -> Result<Tensor> {
        if std::env::var("BOLT_USE_CPU").is_ok() {
             let w = Self::dequantize_cpu(&self.qweight, &self.qzeros, &self.scales)?;
             let w = w.to_dtype(x.dtype())?;
             let out = x.broadcast_matmul(&w)?;
             if let Some(bias) = &self.bias {
                 let bias = bias.to_dtype(x.dtype())?;
                 return out.broadcast_add(&bias);
             }
             return Ok(out);
        }

        let (b, s, k) = x.dims3()?;
        let x_2d = x.reshape((b * s, k))?;
        
        let qweight_u32 = self.qweight.to_dtype(DType::U32)?;
        let qzeros_u32 = self.qzeros.to_dtype(DType::U32)?;
        let scales_f16 = self.scales.to_dtype(DType::F16)?;
        
        let w_dequant = crate::layers::kernels::dequantize_awq(
            &qweight_u32, 
            &qzeros_u32,
            &scales_f16, 
            None,
            self.qweight.dim(0)?,     // in_dim (K)
            self.qweight.dim(1)? * 8, // out_dim (N)
            128 // group_size
        )?;
        
        if std::env::var("BOLT_DEBUG").is_ok() {
            let w_f32 = w_dequant.to_dtype(candle_core::DType::F32)?;
            let mean = w_f32.mean_all()?.to_scalar::<f32>()?;
            let sum = w_f32.abs()?.sum_all()?.to_scalar::<f32>()?;
            let n = (w_dequant.dim(0)? * w_dequant.dim(1)?) as f32;
            let avg_abs = sum / n;
            tracing::debug!("AWQ: shape={:?}, mean={:.6}, avg_abs={:.6}", 
                      w_dequant.dims(), mean, avg_abs);
        }
        
        let out = x_2d.matmul(&w_dequant)?;
        let out = out.reshape((b, s, self.scales.dim(1)?))?;

        if let Some(bias) = &self.bias {
            out.broadcast_add(bias)
        } else {
            Ok(out)
        }
    }

    fn dequantize_cpu(qweight: &Tensor, qzeros: &Tensor, scales: &Tensor) -> Result<Tensor> {
        let (k, n_packed) = qweight.dims2()?;
        let n = n_packed * 8;
        let group_size = 128;
        
        let qw = qweight.to_vec2::<u32>()?;
        let qz = qzeros.to_vec2::<u32>()?;
        let sc = scales.to_vec2::<half::f16>()?;
        
        let mut out = vec![0.0f32; k * n];
        
        for i_k in 0..k {
             let g_idx = i_k / group_size;
             for (i_n_packed, &w_packed) in qw[i_k].iter().enumerate() {
                 let i_n_base = i_n_packed * 8;
                 let z_packed = qz[g_idx][i_n_packed];
                 let awq_reverse_order: [usize; 8] = [0, 4, 1, 5, 2, 6, 3, 7];

                 for (j, &nibble_idx) in awq_reverse_order.iter().enumerate() {
                     let i_n = i_n_base + j;
                     let shift = nibble_idx * 4;
                     let w_val = (w_packed >> shift) & 0xF;
                     let z_val = (z_packed >> shift) & 0xF;
                     let s_val = sc[g_idx][i_n].to_f32();
                     let val = (w_val as f32 - z_val as f32) * s_val;
                     out[i_k * n + i_n] = val;
                 }
             }
        }
        
        let t = Tensor::from_vec(out, (k, n), qweight.device())?;
        let t = t.to_dtype(DType::F16)?;
        Ok(t)
    }
}