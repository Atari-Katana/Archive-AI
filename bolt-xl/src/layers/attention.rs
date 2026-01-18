use candle_core::{Tensor, Result, DType, Device};

/// Efficient attention layer using FlashAttention-2
pub struct Attention {
    /// Number of attention heads
    pub num_heads: usize,
    /// Number of key/value heads (for GQA)
    pub num_kv_heads: usize,
    /// Dimension per head
    pub head_dim: usize,
    /// Scaling factor for attention
    pub scale: f32,
    /// Optional logit softcapping
    pub softcap: Option<f64>,
}

impl Attention {
    pub fn new(num_heads: usize, num_kv_heads: usize, head_dim: usize, scale: f64, softcap: Option<f64>) -> Self {
        Self {
            num_heads,
            num_kv_heads,
            head_dim,
            scale: scale as f32,
            softcap,
        }
    }

    /// Forward pass using scaled dot-product attention (SDPA)
    ///
    /// # Arguments
    /// * `q` - Query tensor [Batch, s_q, NumHeads, HeadDim]
    /// * `k` - Key tensor [Batch, s_kv, NumKVHeads, HeadDim]
    /// * `v` - Value tensor [Batch, s_kv, NumKVHeads, HeadDim]
    /// * `k_cache` - Key cache for paged attention (TODO: implement paged attention)
    /// * `v_cache` - Value cache for paged attention (TODO: implement paged attention)
    /// * `block_table` - Block table for paged attention (TODO: implement paged attention)
    ///
    /// # Returns
    /// Attention output tensor [Batch, s_q, NumHeads * HeadDim]
    pub fn forward(
        &self,
        q: &Tensor,
        k: &Tensor,
        v: &Tensor,
        _k_cache: &mut Tensor,
        _v_cache: &mut Tensor,
        _block_table: &Tensor,
    ) -> Result<Tensor> {
        // TODO: Implement paged attention using k_cache, v_cache, and block_table
        // Currently uses simple causal attention without caching
        if q.device().is_cuda() {
             return self.forward_cuda(q, k, v);
        }
        self.forward_cpu(q, k, v)
    }

    fn forward_cuda(&self, q: &Tensor, k: &Tensor, v: &Tensor) -> Result<Tensor> {
        // Fallback to CPU for now to avoid CUDA build issues
        self.forward_cpu(q, k, v)
    }

    fn forward_cpu(&self, q: &Tensor, k: &Tensor, v: &Tensor) -> Result<Tensor> {
        // SDPA Fallback
        let (b, s_q, _nh, _hd) = q.dims4()?;
        let (_b, s_kv, _nkv, _hd) = k.dims4()?;
        
        let q = q.transpose(1, 2)?.contiguous().unwrap_or_else(|_| q.transpose(1, 2).unwrap());  // [B, NH, s_q, HD]
        let k = k.transpose(1, 2)?.contiguous().unwrap_or_else(|_| k.transpose(1, 2).unwrap());  // [B, NKV, s_kv, HD]
        let v = v.transpose(1, 2)?.contiguous().unwrap_or_else(|_| v.transpose(1, 2).unwrap());  // [B, NKV, s_kv, HD]
        
        // GQA repetition
        let k = if self.num_kv_heads < self.num_heads {
            let n_rep = self.num_heads / self.num_kv_heads;
            k.unsqueeze(2)?.expand((b, self.num_kv_heads, n_rep, s_kv, self.head_dim))?.reshape((b, self.num_heads, s_kv, self.head_dim))?
        } else { k };
        
        let v = if self.num_kv_heads < self.num_heads {
            let n_rep = self.num_heads / self.num_kv_heads;
            v.unsqueeze(2)?.expand((b, self.num_kv_heads, n_rep, s_kv, self.head_dim))?.reshape((b, self.num_heads, s_kv, self.head_dim))?
        } else { v };

        let k_t = k.transpose(2, 3)?.contiguous().unwrap_or_else(|_| k.transpose(2, 3).unwrap());
        let scores = (q.matmul(&k_t)? * (self.scale as f64))?;
        
        // Causal mask (only if s_kv > 1)
        let mask = Self::create_causal_mask(s_q, s_kv, scores.device(), scores.dtype())?;
        let scores = scores.broadcast_add(&mask)?;
        
        let attn_weights = candle_nn::ops::softmax_last_dim(&scores).unwrap_or_else(|_| candle_nn::ops::softmax_last_dim(&scores).unwrap());
        let out = attn_weights.matmul(&v)?; // [B, NH, s_q, HD]
        
        let out = out.transpose(1, 2)?.contiguous().unwrap_or_else(|_| out.transpose(1, 2).unwrap());
        let (b, s, nh, hd) = out.dims4()?;
        let out = out.reshape((b, s, nh * hd))?;
        
        Ok(out)
    }
    
    fn create_causal_mask(s_q: usize, s_kv: usize, device: &Device, dtype: DType) -> Result<Tensor> {
        let mut mask_data = vec![0.0f32; s_q * s_kv];
        for i in 0..s_q {
            for j in 0..s_kv {
                // In causal attention:
                // If s_q == s_kv (prefill), j > i is masked.
                // If s_kv > s_q (decode), the relative position of the current token (idx i in q)
                // is s_kv - s_q + i in the full sequence.
                // We mask j > (s_kv - s_q + i).
                let pos_in_full = s_kv - s_q + i;
                if j > pos_in_full {
                    mask_data[i * s_kv + j] = f32::NEG_INFINITY;
                }
            }
        }
        
        let mask = Tensor::from_vec(mask_data, (s_q, s_kv), device)?;
        let mask = mask.to_dtype(dtype)?;
        let mask = mask.unsqueeze(0)?.unsqueeze(0)?;  // [1, 1, SQ, SKV]
        
        Ok(mask)
    }
}
