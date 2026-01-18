#include <cuda.h>
#include <cuda_runtime.h>

int marlin_cuda(
    const void* A,            // Input matrix A [M × K]
    const void* B,            // Input matrix B [K × N] (weights)
    void* C,                 // Output matrix C [M × N]
    void* s,                 // Workspace buffer for intermediate results
    int prob_m,               // Problem dimension M
    int prob_n,               // Problem dimension N
    int prob_k,               // Problem dimension K
    int groupsize,             // Quantization group size
    int dev,                  // GPU device ID
    cudaStream_t stream,       // CUDA stream for async execution
    int thread_k,              // Thread block dimension K
    int thread_n,              // Thread block dimension N
    int sms,                  // Number of SMs to use
    int max_par               // Maximum parallelism
);
