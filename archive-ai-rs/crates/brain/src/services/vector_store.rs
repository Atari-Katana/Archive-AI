use redis::{AsyncCommands, cmd};
use serde_json::json;
use crate::services::redis_client::RedisService;
use shared::AppConfig;
use anyhow::Result;
use tracing::{info, error, debug};

#[derive(Clone)]
pub struct VectorStore {
    redis: RedisService,
    config: AppConfig,
    client: reqwest::Client,
    index_name: String,
    prefix: String,
}

impl VectorStore {
    pub fn new(redis: RedisService, config: AppConfig) -> Self {
        Self {
            redis,
            config,
            client: reqwest::Client::new(),
            index_name: "memory_index".to_string(),
            prefix: "memory:".to_string(),
        }
    }

    pub async fn create_index(&self) -> Result<()> {
        let mut conn = self.redis.get_connection().await?;
        
        // Check if index exists
        let info: Result<redis::Value, _> = cmd("FT.INFO")
            .arg(&self.index_name)
            .query_async(&mut conn)
            .await;

        if info.is_ok() {
            info!("Index '{}' already exists", self.index_name);
            return Ok(());
        }

        info!("Creating index '{}'...", self.index_name);
        
        // FT.CREATE memory_index ON HASH PREFIX 1 memory: SCHEMA ...
        let _: () = cmd("FT.CREATE")
            .arg(&self.index_name)
            .arg("ON").arg("HASH")
            .arg("PREFIX").arg("1").arg(&self.prefix)
            .arg("SCHEMA")
            .arg("message").arg("TEXT")
            .arg("embedding").arg("VECTOR").arg("HNSW").arg("6")
                .arg("TYPE").arg("FLOAT32")
                .arg("DIM").arg("384")
                .arg("DISTANCE_METRIC").arg("COSINE")
            .arg("perplexity").arg("NUMERIC").arg("SORTABLE")
            .arg("surprise_score").arg("NUMERIC").arg("SORTABLE")
            .arg("timestamp").arg("NUMERIC").arg("SORTABLE")
            .arg("session_id").arg("TAG")
            .arg("metadata").arg("TEXT")
            .query_async(&mut conn)
            .await?;

        Ok(())
    }

    pub async fn get_embedding(&self, text: &str) -> Result<Vec<f32>> {
        let url = format!("{}/v1/embeddings", self.config.vorpal_url);
        let payload = json!({
            "input": text,
            "model": self.config.vorpal_model
        });

        let res = self.client.post(&url)
            .json(&payload)
            .send()
            .await?;

        if !res.status().is_success() {
            return Err(anyhow::anyhow!("Embedding service error: {}", res.status()));
        }

        let body: serde_json::Value = res.json().await?;
        
        let embedding = body["data"][0]["embedding"]
            .as_array()
            .ok_or(anyhow::anyhow!("Invalid embedding response format"))?
            .iter()
            .map(|v| v.as_f64().unwrap_or(0.0) as f32)
            .collect();

        Ok(embedding)
    }

    pub async fn search_similar(&self, query_vec: &[f32], limit: usize) -> Result<Vec<serde_json::Value>> {
        let mut conn = self.redis.get_connection().await?;
        
        // Convert Vec<f32> to bytes
        let vec_bytes: Vec<u8> = query_vec.iter()
            .flat_map(|&f| f.to_le_bytes().to_vec())
            .collect();

        let query = format!("*=>[KNN {} @embedding $vec AS score]", limit);

        let results: redis::Value = cmd("FT.SEARCH")
            .arg(&self.index_name)
            .arg(query)
            .arg("PARAMS").arg("2").arg("vec").arg(vec_bytes)
            .arg("RETURN").arg("6").arg("message").arg("perplexity").arg("surprise_score").arg("timestamp").arg("session_id").arg("score")
            .arg("SORTBY").arg("score")
            .arg("DIALECT").arg("2")
            .arg("LIMIT").arg("0").arg(limit.to_string())
            .query_async(&mut conn)
            .await?;

        // Parse RediSearch results (Format: [count, key1, [fields1], key2, [fields2]...])
        // This parsing is tedious in Rust but necessary.
        // For brevity, I'll implement a basic parser.
        
        match results {
            redis::Value::Bulk(items) => {
                if items.is_empty() { return Ok(vec![]); }
                // let count = match &items[0] { redis::Value::Int(c) => *c, _ => 0 };
                let mut memories = Vec::new();
                
                for i in (1..items.len()).step_by(2) {
                    // let key = &items[i];
                    let fields = &items[i+1];
                    
                    if let redis::Value::Bulk(f_items) = fields {
                        let mut map = serde_json::Map::new();
                        for j in (0..f_items.len()).step_by(2) {
                            if let (redis::Value::Data(name), redis::Value::Data(val)) = (&f_items[j], &f_items[j+1]) {
                                let name_str = String::from_utf8_lossy(name).to_string();
                                let val_str = String::from_utf8_lossy(val).to_string();
                                map.insert(name_str, serde_json::Value::String(val_str));
                            }
                        }
                        memories.push(serde_json::Value::Object(map));
                    }
                }
                Ok(memories)
            },
            _ => Ok(vec![])
        }
    }
    
    pub async fn store_memory(
        &self, 
        message: &str, 
        perplexity: f64, 
        surprise_score: f64,
        session_id: &str,
        metadata: serde_json::Value
    ) -> Result<String> {
        let mut conn = self.redis.get_connection().await?;
        
        let embedding = self.get_embedding(message).await?;
        let vec_bytes: Vec<u8> = embedding.iter()
            .flat_map(|&f| f.to_le_bytes().to_vec())
            .collect();

        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)?
            .as_secs_f64();
            
        let key = format!("{}{}", self.prefix, (timestamp * 1000.0) as u64);

        let _: () = conn.hset_multiple(&key, &[
            ("message", message),
            ("perplexity", &perplexity.to_string()),
            ("surprise_score", &surprise_score.to_string()),
            ("timestamp", &timestamp.to_string()),
            ("session_id", session_id),
            ("metadata", &metadata.to_string()),
        ]).await?;
        
        // Set binary embedding separately to avoid string conversion issues in hset_multiple
        let _: () = conn.hset(&key, "embedding", vec_bytes).await?;

        debug!("Stored memory: {}", key);
        Ok(key)
    }
}