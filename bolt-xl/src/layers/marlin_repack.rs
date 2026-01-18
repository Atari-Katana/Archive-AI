use candle_core::{Tensor, Device, Result};

pub fn repack_awq_to_marlin(qweight: &Tensor) -> Result<Tensor> {
    tracing::debug!("repack_awq_to_marlin called");
    let device = qweight.device();
    let qweight_cpu = qweight.to_device(&Device::Cpu)?;
    let (k, n_packed) = qweight_cpu.dims2()?;
    tracing::debug!("dims K={} N_packed={}", k, n_packed);
    let n = n_packed * 8;

    let sl = qweight_cpu.to_dtype(candle_core::DType::U32)?.flatten_all()?.to_vec1::<u32>()?;
    tracing::debug!("got slice len {}", sl.len());
    
    let mut unpacked = vec![0u32; k * n]; 
    for (i, &val) in sl.iter().enumerate().take(k * n_packed) {
        let row = i / n_packed;
        let col_pack = i % n_packed;
        for b in 0..8 {
            let elem = (val >> (b * 4)) & 0xF;
            unpacked[row * n + col_pack * 8 + b] = elem;
        }
    }

    println!("DEBUG: starting permutation logic");
    
    let mut perm = [0usize; 16];
    for i in 0..8 {
        perm[2 * i] = i;
        perm[2 * i + 1] = 8 + i;
    }
    
    let mut repacked = vec![0u32; k * n_packed];
    tracing::debug!("allocated repacked size {}", repacked.len());

    let block_size = 16;
    if k % block_size != 0 {
        candle_core::bail!("Dimensions K={} not divisible by Marlin tile size 16", k);
    }

    tracing::debug!("processing row blocks...");
    
    for row_block in 0..(k / block_size) {
        let base_row = row_block * block_size;
        for r in 0..block_size {
            let src_r = base_row + perm[r]; 
            if src_r >= k { continue; }
            
            for c in 0..n_packed {
                repacked[(base_row + r) * n_packed + c] = sl[src_r * n_packed + c];
            }
        }
    }
    
    let repacked_tensor = Tensor::from_vec(repacked, (k, n_packed), &Device::Cpu)?;
    repacked_tensor.to_device(device)
}