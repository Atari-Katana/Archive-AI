use candle_core::{Tensor, Result, DType, Device};

#[derive(Clone)]
pub struct RotaryEmbedding {
    cos: Tensor,
    sin: Tensor,
}

impl RotaryEmbedding {
    pub fn new(
        dim: usize,
        max_seq_len: usize,
        base: f32,
        device: &Device,
        dtype: DType,
    ) -> Result<Self> {
        let inv_freq: Vec<f32> = (0..dim)
            .step_by(2)
            .map(|i| 1.0 / base.powf(i as f32 / dim as f32))
            .collect();
        let inv_freq_len = inv_freq.len();
        let inv_freq = Tensor::from_vec(inv_freq, (1, inv_freq_len), device)?.to_dtype(DType::F32)?;
        
        let t: Vec<f32> = (0..max_seq_len).map(|i| i as f32).collect();
        let t_len = t.len();
        let t = Tensor::from_vec(t, (t_len, 1), device)?.to_dtype(DType::F32)?;
        
        let freqs = t.matmul(&inv_freq)?; // [MaxSeq, Dim/2]
        
        // Concat to [MaxSeq, Dim]
        let freqs = Tensor::cat(&[&freqs, &freqs], 1)?;
        
        let cos = freqs.cos()?.to_dtype(dtype)?;
        let sin = freqs.sin()?.to_dtype(dtype)?;
        
        Ok(Self { cos, sin })
    }

    pub fn forward(&self, q: &Tensor, k: &Tensor, pos: &Tensor) -> Result<(Tensor, Tensor)> {
        // q: [Batch, Seq, NumHeads, HeadDim]
        // k: [Batch, Seq, NumKVHeads, HeadDim]
        // pos: [Batch, Seq] (indices)
        
        let (_b, s, _nh, _hd) = q.dims4()?;
        
        // Gather cos/sin based on pos
        // self.cos: [MaxSeq, HeadDim]
        // Gather is tricky in candle if pos has batch dimension.
        // For now, simplify: if batch=1, just slice.
        // In our coherence test, batch is 1.
        
        let pos_flat = pos.flatten_all()?;
        let cos = self.cos.index_select(&pos_flat, 0)?; // [TotalTokens, HeadDim]
        let sin = self.sin.index_select(&pos_flat, 0)?; // [TotalTokens, HeadDim]
        
        // Reshape cos/sin to [Batch, Seq, 1, HeadDim]
        let (b, _) = pos.dims2()?;
        let cos = cos.reshape((b, s, 1, cos.dim(1)?))?;
        let sin = sin.reshape((b, s, 1, sin.dim(1)?))?;
        
        let q_rot = self.apply_rope(q, &cos, &sin)?;
        let k_rot = self.apply_rope(k, &cos, &sin)?;
        
        Ok((q_rot, k_rot))
    }
    
    fn apply_rope(&self, x: &Tensor, cos: &Tensor, sin: &Tensor) -> Result<Tensor> {
        // x: [B, S, NH, HD]
        // cos, sin: [B, S, 1, HD]
        
        let rotated_x = self.rotate_half(x)?;
        
        // x * cos + rotated_x * sin
        let out = (x.broadcast_mul(cos)? + rotated_x.broadcast_mul(sin)?)?;
        Ok(out)
    }
    
    fn rotate_half(&self, x: &Tensor) -> Result<Tensor> {
        let last_dim = x.dim(x.rank() - 1)?;
        let x1 = x.narrow(x.rank() - 1, 0, last_dim / 2)?;
        let x2 = x.narrow(x.rank() - 1, last_dim / 2, last_dim / 2)?;
        
        // cat([-x2, x1], dim=-1)
        Tensor::cat(&[&x2.neg()?, &x1], x.rank() - 1)
    }
}
