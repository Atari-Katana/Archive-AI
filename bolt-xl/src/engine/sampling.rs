use candle_core::{Tensor, Result, DType};
use rand::{rngs::StdRng, SeedableRng, Rng};

#[derive(Debug, Clone)]
pub struct SamplingParams {
    pub temperature: f64,
    pub top_p: f64,
    pub top_k: usize,
    pub seed: u64,
}

impl Default for SamplingParams {
    fn default() -> Self {
        Self {
            temperature: 0.7,
            top_p: 0.9,
            top_k: 50,
            seed: 42,
        }
    }
}

pub struct Sampler {
    rng: StdRng,
}

impl Sampler {
    pub fn new(seed: u64) -> Self {
        Self {
            rng: StdRng::seed_from_u64(seed),
        }
    }

    pub fn sample(&mut self, logits: &Tensor, params: &SamplingParams) -> Result<u32> {
        let logits = logits.to_dtype(DType::F32)?;
        let logits = logits.squeeze(0)?; // [Vocab]
        let mut logits_vec: Vec<f32> = logits.to_vec1()?;

        // Temperature
        let temp = params.temperature as f32;
        if temp < 1e-5 {
            let argmax = logits_vec.iter()
                .enumerate()
                .max_by(|(_, a), (_, b)| a.total_cmp(b))
                .map(|(index, _)| index)
                .unwrap_or(0);
            return Ok(argmax as u32);
        }
        for p in logits_vec.iter_mut() { *p /= temp; }

        // Softmax
        let max_val = logits_vec.iter().fold(f32::NEG_INFINITY, |a, &b| a.max(b));
        let exp_props: Vec<f32> = logits_vec.iter().map(|&p| (p - max_val).exp()).collect();
        let exp_sum: f32 = exp_props.iter().sum();
        let probs: Vec<f32> = exp_props.iter().map(|p| p / exp_sum).collect();

        // Sampling (Weighted Random)
        let r_val: f32 = self.rng.gen_range(0.0..1.0);
        let mut cdf = 0.0;
        for (i, p) in probs.iter().enumerate() {
            cdf += p;
            if r_val <= cdf {
                return Ok(i as u32);
            }
        }
        Ok(probs.len() as u32 - 1)
    }
}
