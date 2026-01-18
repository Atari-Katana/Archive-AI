pub mod attention;
pub mod linear;
pub mod rotation;
pub mod quantization;
#[cfg(feature = "cuda")]
pub mod kernels;
pub mod marlin_repack;
#[cfg(feature = "cuda")]
pub mod marlin;

#[cfg(not(feature = "cuda"))]
pub mod kernels_stub {
    use candle_core::{Tensor, Result};
    pub fn dequantize_awq(
        _qweight: &Tensor,
        _qzeros: &Tensor,
        _scales: &Tensor,
        _g_idx: Option<&Tensor>,
        _in_dim: usize,
        _out_dim: usize,
        _group_size: usize,
    ) -> Result<Tensor> {
        candle_core::bail!("AWQ dequantize kernel requires CUDA")
    }
}

#[cfg(not(feature = "cuda"))]
pub use kernels_stub as kernels;

#[cfg(not(feature = "cuda"))]
pub mod marlin_stub {
    use candle_core::{Tensor, Result};
    pub struct MarlinLinear {
        pub qweight: Tensor,
        pub scales: Tensor,
        pub workspace: Tensor,
        pub in_features: usize,
        pub out_features: usize,
        pub group_size: usize,
    }
    
    impl MarlinLinear {
        pub fn forward(&self, _x: &Tensor) -> Result<Tensor> {
            candle_core::bail!("Marlin requires CUDA")
        }
    }
}

#[cfg(not(feature = "cuda"))]
pub use marlin_stub as marlin;

