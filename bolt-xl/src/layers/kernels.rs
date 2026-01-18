#[cfg(feature = "cuda")]
use candle_core::{Tensor, Result, cuda_backend::cudarc::driver::DevicePtr};

#[cfg(feature = "cuda")]
extern "C" {
    fn launch_dequantize_awq(
        qweight: *const u32,
        qzeros: *const u32,
        scales: *const half::f16,
        g_idx: *const i32,
        output: *mut half::f16,
        in_dim: i32,
        out_dim: i32,
        group_size: i32,
        stream: *mut std::ffi::c_void,
    );
    
    fn cudaDeviceSynchronize() -> i32;
}

#[cfg(feature = "cuda")]
pub fn dequantize_awq(
    qweight: &Tensor,
    qzeros: &Tensor,
    scales: &Tensor,
    g_idx: Option<&Tensor>,
    in_dim: usize,
    out_dim: usize,
    group_size: usize,
) -> Result<Tensor> {
    let device = qweight.device();
    if !device.is_cuda() {
         candle_core::bail!("AWQ dequantize kernel only supports CUDA");
    }
    
    let (qw_storage, _) = qweight.storage_and_layout();
    let (qz_storage, _) = qzeros.storage_and_layout();
    let (s_storage, _) = scales.storage_and_layout();
    
    let qw_ptr = match &*qw_storage {
        candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<u32>()?.device_ptr(),
        _ => candle_core::bail!("qweight must be on CUDA"),
    };
    
    let qz_ptr = match &*qz_storage {
        candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<u32>()?.device_ptr(),
        _ => candle_core::bail!("qzeros must be on CUDA"),
    };
    
    let s_ptr = match &*s_storage {
        candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<half::f16>()?.device_ptr(),
        _ => candle_core::bail!("scales must be on CUDA"),
    };

    let g_idx_ptr = if let Some(g) = g_idx {
        let (g_storage, _) = g.storage_and_layout();
        match &*g_storage {
            candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<u32>()?.device_ptr(),
            _ => 0, 
        }
    } else {
        0
    };
    
    let output = Tensor::zeros((in_dim, out_dim), candle_core::DType::F16, device)?;
    
    {
        let (out_storage, _out_layout) = output.storage_and_layout();
        let out_ptr = match &*out_storage {
            candle_core::Storage::Cuda(c) => *c.as_cuda_slice::<half::f16>()?.device_ptr(),
            _ => candle_core::bail!("output must be on CUDA"),
        };
        
        let stream = std::ptr::null_mut();

        unsafe {
            launch_dequantize_awq(
                qw_ptr as *const u32,
                qz_ptr as *const u32,
                s_ptr as *const half::f16,
                g_idx_ptr as *const i32,
                out_ptr as *mut half::f16,
                in_dim as i32,
                out_dim as i32,
                group_size as i32,
                stream
            );
            cudaDeviceSynchronize();
        }
    }

    Ok(output)
}
