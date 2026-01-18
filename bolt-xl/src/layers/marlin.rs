#[cfg(feature = "cuda")]
use candle_core::{Tensor, Result, DType, Device};
#[cfg(feature = "cuda")]
use candle_core::cuda_backend::cudarc::driver::DevicePtr;

#[cfg(feature = "cuda")]
extern "C" {
    fn cudaDeviceSynchronize() -> i32;
    fn launch_marlin(
        A: *const std::ffi::c_void,
        B: *const std::ffi::c_void,
        C: *mut std::ffi::c_void,
        s: *const std::ffi::c_void,
        prob_m: i32,
        prob_n: i32,
        prob_k: i32,
        workspace: *mut std::ffi::c_void,
        groupsize: i32,
        dev: i32,
        stream: u64,
        thread_k: i32,
        thread_n: i32,
        sms: i32,
        max_par: i32
    ) -> i32;
}

#[cfg(feature = "cuda")]
pub struct MarlinLinear {
    pub qweight: Tensor,
    pub scales: Tensor,
    pub workspace: Tensor,
    pub in_features: usize,
    pub out_features: usize,
    pub group_size: usize,
}

#[cfg(feature = "cuda")]
impl MarlinLinear {
    pub fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let (b_sz, seq_len, in_dim) = x.dims3()?;
        if in_dim != self.in_features {
             candle_core::bail!("Mismatch in input features: {} vs {}", in_dim, self.in_features);
        }
        
        let x_flat = x.flatten_to(1)?;
        let prob_m = (b_sz * seq_len) as i32;
        let prob_k = self.in_features as i32;
        let prob_n = self.out_features as i32;
        
        let device = x.device();
        let dev_id = match device {
            Device::Cuda(c) => c.ordinal() as i32,
            _ => candle_core::bail!("Marlin requires CUDA"),
        };
        
        let out_tensor = Tensor::zeros((b_sz, seq_len, self.out_features), DType::F16, device)?;
        let out_flat = out_tensor.flatten_to(1)?; 

        let a_ptr = {
            let (s, _) = x_flat.storage_and_layout();
            match &*s {
                candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<half::f16>()?.device_ptr() as *const std::ffi::c_void,
                _ => candle_core::bail!("Input must be CUDA F16"),
            }
        };

        let b_ptr = {
             let (s, _) = self.qweight.storage_and_layout();
             match &*s {
                candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<u32>()?.device_ptr() as *const std::ffi::c_void,
                _ => candle_core::bail!("qweight must be CUDA U32"),
             }
        };

        let c_ptr = {
             let (s, _) = out_flat.storage_and_layout();
             match &*s {
                candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<half::f16>()?.device_ptr() as *mut std::ffi::c_void,
                _ => candle_core::bail!("Output must be CUDA F16"),
             }
        };

        let s_ptr = {
             let (s, _) = self.scales.storage_and_layout();
             match &*s {
                candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<half::f16>()?.device_ptr() as *const std::ffi::c_void,
                _ => candle_core::bail!("Scales must be CUDA F16"),
             }
        };

        let w_ptr = {
             let (s, _) = self.workspace.storage_and_layout();
             match &*s {
                candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<u32>()?.device_ptr() as *mut std::ffi::c_void,
                _ => candle_core::bail!("Workspace must be CUDA U32"),
             }
        };

        unsafe {
            let stream = 0u64;
            launch_marlin(
                a_ptr, b_ptr, c_ptr, s_ptr,
                prob_m, prob_n, prob_k, w_ptr,
                self.group_size as i32, dev_id, stream,
                -1, -1, -1, 16
            );
            cudaDeviceSynchronize();
        }
        
        Ok(out_tensor)
    }
}
