#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <stdint.h>

// AWQ GEMM Reverse Order: maps logical output position to packed nibble position
// Packed order is [0,2,4,6,1,3,5,7], so to reverse we need [0,4,1,5,2,6,3,7]
// i.e., logical 0 -> nibble 0, logical 1 -> nibble 4, logical 2 -> nibble 1, logical 3 -> nibble 5, etc.
__constant__ int AWQ_REVERSE_ORDER[8] = {0, 4, 1, 5, 2, 6, 3, 7};

// AWQ Dequantization Kernel
// Weights: uint32_t packed [in_dim, out_dim / 8]
// Zeros: uint32_t packed [in_dim / group_size, out_dim / 8]
// Scales: half [in_dim / group_size, out_dim]
// Output: half [in_dim, out_dim]

// Each thread handles 8 elements (1 uint32 block)
 extern "C" __global__ void dequantize_awq_kernel(
    const uint32_t* __restrict__ qweight,
    const uint32_t* __restrict__ qzeros,
    const half* __restrict__ scales,
    const int* __restrict__ g_idx,
    half* __restrict__ output,
    int in_dim,
    int out_dim,
    int group_size
) {
    int out_packed_dim = out_dim / 8;
    
    // Grid: (x, y) -> (out_packed_dim, in_dim)
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col_packed = blockIdx.x * blockDim.x + threadIdx.x;

    if (row >= in_dim || col_packed >= out_packed_dim || !qweight || !qzeros || !scales) return;

    // Use g_idx if present, else standard division with validation
    int g = 0;
    if (g_idx) {
        int g_val = g_idx[row];
        g = (g_val >= 0) ? g_val : (row / group_size);
    } else {
        g = row / group_size;
    }
    // Load packed weights
    uint32_t qw = qweight[row * out_packed_dim + col_packed];

    // Load packed zeros
    uint32_t qz = qzeros[g * out_packed_dim + col_packed];

    // Process 8 elements
    #pragma unroll
    for (int k = 0; k < 8; k++) {
        int col = col_packed * 8 + k;

        // Apply AWQ GEMM reverse order to get the correct nibble position
        int nibble_idx = AWQ_REVERSE_ORDER[k];
        int shift = nibble_idx * 4;

        uint32_t w_val = (qw >> shift) & 0xF;
        uint32_t z_val = (qz >> shift) & 0xF;

        // Load scale
        half scale = scales[g * out_dim + col];

        // Dequantize: (w - z) * s
        float val = (float(w_val) - float(z_val)) * __half2float(scale);

        output[row * out_dim + col] = __float2half(val);
    }
}

extern "C" void launch_dequantize_awq(
    const uint32_t* qweight,
    const uint32_t* qzeros,
    const half* scales,
    const int* g_idx,
    half* output,
    int in_dim,
    int out_dim,
    int group_size,
    cudaStream_t stream
) {
    if (!stream) {
        return;
    }

    dim3 block(32, 32);
    // Grid covers [out_dim/8, in_dim]
    int out_packed = out_dim / 8;
    dim3 grid(
        (out_packed + block.x - 1) / block.x,
        (in_dim + block.y - 1) / block.y
    );

    dequantize_awq_kernel<<<grid, block, 0, stream>>>(
        qweight, qzeros, scales, g_idx, output, in_dim, out_dim, group_size
    );
}
