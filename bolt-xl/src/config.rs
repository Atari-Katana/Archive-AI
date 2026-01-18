use serde::Deserialize;

/// Engine configuration loaded from YAML or Defaults
#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub model: String,
    pub max_num_batched_tokens: usize,
    pub max_num_seqs: usize,
    pub max_model_len: usize,
    pub gpu_memory_utilization: f64,
    pub tensor_parallel_size: usize,
    pub kvcache_block_size: usize,
    pub speculative_decoding: bool,
    pub draft_model: Option<String>,
    pub num_speculative_tokens: usize,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            model: "TinyLlama/TinyLlama-1.1B-Chat-v1.0".to_string(),
            max_num_batched_tokens: 4096,
            max_num_seqs: 256,
            max_model_len: 2048,
            gpu_memory_utilization: 0.9,
            tensor_parallel_size: 1,
            kvcache_block_size: 16,
            speculative_decoding: false,
            draft_model: None,
            num_speculative_tokens: 5,
        }
    }
}

impl Config {
    pub fn validate(&self) -> Result<(), String> {
        if self.max_num_batched_tokens == 0 {
            return Err("max_num_batched_tokens must be > 0".to_string());
        }
        if self.max_num_seqs == 0 {
            return Err("max_num_seqs must be > 0".to_string());
        }
        if self.max_model_len == 0 {
            return Err("max_model_len must be > 0".to_string());
        }
        if !(0.0..=1.0).contains(&self.gpu_memory_utilization) {
            return Err("gpu_memory_utilization must be between 0 and 1".to_string());
        }
        if self.tensor_parallel_size == 0 {
            return Err("tensor_parallel_size must be > 0".to_string());
        }
        if self.kvcache_block_size == 0 {
            return Err("kvcache_block_size must be > 0".to_string());
        }
        if self.speculative_decoding && self.draft_model.is_none() {
            return Err("draft_model must be provided when speculative_decoding is enabled".to_string());
        }
        if self.num_speculative_tokens == 0 {
            return Err("num_speculative_tokens must be > 0".to_string());
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config_valid() {
        let config = Config::default();
        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_invalid_gpu_util() {
        let config = Config {
            gpu_memory_utilization: 1.5,
            ..Default::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_speculative_decoding_validation() {
        let mut config = Config {
            speculative_decoding: true,
            draft_model: None,
            ..Default::default()
        };
        assert!(config.validate().is_err());
        
        config.draft_model = Some("dummy".to_string());
        assert!(config.validate().is_ok());
    }
}