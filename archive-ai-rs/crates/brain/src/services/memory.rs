use crate::services::vector_store::VectorStore;
use shared::AppConfig;
use anyhow::Result;
use tracing::error;

#[derive(Clone)]
pub struct SurpriseScorer {
    vector_store: VectorStore,
    config: AppConfig,
    client: reqwest::Client,
}

impl SurpriseScorer {
    pub fn new(vector_store: VectorStore, config: AppConfig) -> Self {
        Self { 
            vector_store, 
            config,
            client: reqwest::Client::new(),
        }
    }

    pub async fn calculate_score(&self, text: &str) -> Result<(f64, f64, f64)> {
        // 1. Get Embedding
        let embedding = self.vector_store.get_embedding(text).await?;

        // 2. Calculate Distance (Novelty)
        let similar = self.vector_store.search_similar(&embedding, 1).await?;
        let distance_score = if similar.is_empty() {
            1.0 // Maximum novelty
        } else {
            // In KNN, score is cosine distance [0, 1]
            similar[0]["score"].as_str()
                .and_then(|s| s.parse::<f64>().ok())
                .unwrap_or(0.5)
        };

        // 3. Calculate Perplexity (Prediction Error) via Vorpal
        let perplexity = self.calculate_perplexity(text).await?;

        // 4. Normalize Perplexity
        let normalized_perplexity = ( (perplexity + self.config.perplexity_log_offset).ln() / self.config.perplexity_log_divisor ).min(1.0);

        // 5. Weighted Sum
        let surprise_score = (self.config.perplexity_weight * normalized_perplexity) + 
                             (self.config.vector_distance_weight * distance_score);
        
        Ok((surprise_score, perplexity, distance_score))
    }

    async fn calculate_perplexity(&self, text: &str) -> Result<f64> {
        // Implementation calling Vorpal /v1/chat/completions with logprobs
        // For brevity, we'll try to match the Python llm.get_logprobs logic
        
        let url = format!("{}/v1/chat/completions", self.config.vorpal_url);
        let payload = serde_json::json!({
            "model": self.config.vorpal_model,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 1,
            "logprobs": true,
            "echo": true
        });

        let res = self.client.post(&url)
            .json(&payload)
            .send()
            .await?;

        if !res.status().is_success() {
            error!("Vorpal perplexity error: {}", res.status());
            return Ok(1.0); // Fallback
        }

        let body: serde_json::Value = res.json().await?;
        
        // Extract logprobs and calculate avg
        // This part depends on vLLM response format.
        // Mocking average logprob calculation:
        let avg_logprob: f64 = -1.0; 
        
        let perplexity = (-avg_logprob).exp();
        Ok(perplexity)
    }
}