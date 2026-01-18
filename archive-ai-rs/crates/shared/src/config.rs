use serde::{Deserialize, Serialize};
use config::{Config, ConfigError, Environment};
use std::env;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct AppConfig {
    // Service URLs
    pub vorpal_url: String,
    pub goblin_url: String,
    pub bolt_xl_url: String,
    pub sandbox_url: String,
    pub voice_url: String,
    pub bifrost_url: String,
    pub redis_url: String,
    pub public_url: String,

    // Feature Flags
    pub async_memory: bool,
    pub enable_voice: bool,
    pub archive_enabled: bool,

    // Settings
    pub log_level: String,
    pub vorpal_model: String,
    pub max_tokens: usize,
    
    // Archival
    pub archive_days_threshold: i64,
    pub archive_keep_recent: i64,
    
    // Redis Keys
    pub redis_stream_key: String,

    // Surprise Score Constants
    pub surprise_threshold: f64,
    pub perplexity_weight: f64,
    pub vector_distance_weight: f64,
    pub perplexity_log_offset: f64,
    pub perplexity_log_divisor: f64,
}

impl AppConfig {
    pub fn new() -> Result<Self, ConfigError> {
        let _run_mode = env::var("RUN_MODE").unwrap_or_else(|_| "development".into());

        let s = Config::builder()
            // Start with defaults
            .set_default("vorpal_url", "http://archive-vorpal:8000")?
            .set_default("goblin_url", "http://goblin:8080")?
            .set_default("bolt_xl_url", "http://archive-bolt-xl:3000")?
            .set_default("sandbox_url", "http://sandbox:8000")?
            .set_default("voice_url", "http://voice:8000")?
            .set_default("bifrost_url", "http://bifrost:8080")?
            .set_default("redis_url", "redis://redis:6379")?
            .set_default("public_url", "http://localhost:8080")?
            .set_default("async_memory", true)?
            .set_default("enable_voice", true)?
            .set_default("archive_enabled", true)?
            .set_default("log_level", "INFO")?
            .set_default("vorpal_model", "Qwen/Qwen2.5-3B-Instruct")?
            .set_default("max_tokens", 1024)?
            .set_default("archive_days_threshold", 30)?
            .set_default("archive_keep_recent", 1000)?
            .set_default("redis_stream_key", "session:input_stream")?
            .set_default("surprise_threshold", 0.7)?
            .set_default("perplexity_weight", 0.6)?
            .set_default("vector_distance_weight", 0.4)?
            .set_default("perplexity_log_offset", 1.0)?
            .set_default("perplexity_log_divisor", 5.0)?

            // Add Environment Variables override (e.g. VORPAL_URL)
            .add_source(Environment::default())
            .build()?;

        s.try_deserialize()
    }
}