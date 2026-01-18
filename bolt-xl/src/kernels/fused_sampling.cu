#include <cfloat>
#include <curand_kernel.h>

extern "C" __global__ void fused_sampling_kernel(
    const float* logits,  // [batch_size, vocab_size]
    float* probs,         // [batch_size, vocab_size] (temporary)
    int* sampled_tokens,  // [batch_size]
    float* temperatures,  // [batch_size] or scalar
    float* top_p,         // [batch_size] or scalar
    int batch_size,
    int vocab_size,
    unsigned long long* rng_state  // for random number generation
) {
    int batch_idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (batch_idx >= batch_size) return;

    // Load logits for this batch
    const float* batch_logits = logits + batch_idx * vocab_size;
    float temp = temperatures[batch_size > 1 ? batch_idx : 0];
    // float p = top_p[batch_size > 1 ? batch_idx : 0];  // TODO: implement top-p sampling

    // Find max for numerical stability
    float max_logit = -FLT_MAX;
    for (int i = 0; i < vocab_size; ++i) {
        max_logit = fmaxf(max_logit, batch_logits[i]);
    }

    // Compute exp and sum
    float sum_exp = 0.0f;
    for (int i = 0; i < vocab_size; ++i) {
        float exp_val = expf((batch_logits[i] - max_logit) / temp);
        probs[batch_idx * vocab_size + i] = exp_val;
        sum_exp += exp_val;
    }

    // Normalize to probabilities
    for (int i = 0; i < vocab_size; ++i) {
        probs[batch_idx * vocab_size + i] /= sum_exp;
    }

    // Top-p sampling (nucleus sampling)
    // Simplified: sort and cumulative sum
    // For simplicity, assume we do multinomial sampling directly
    // Simple LCG for randomness (for simplicity)
    unsigned long long state = rng_state[batch_idx];
    state = (state * 1103515245ULL + 12345ULL) % (1ULL << 31);
    float rand_val = (state % 1000000) / 1000000.0f;
    rng_state[batch_idx] = state;

    float cumsum = 0.0f;
    for (int i = 0; i < vocab_size; ++i) {
        cumsum += probs[batch_idx * vocab_size + i];
        if (cumsum >= rand_val || i == vocab_size - 1) {
            sampled_tokens[batch_idx] = i;
            break;
        }
    }
}
