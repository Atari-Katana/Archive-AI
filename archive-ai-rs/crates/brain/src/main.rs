use axum::{routing::get, Router};
use std::net::SocketAddr;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use shared::AppConfig;

mod services;
mod workers;
mod routes;
mod agents;

use services::redis_client::RedisService;
use services::vector_store::VectorStore;

#[derive(Clone)]
pub struct AppState {
    pub config: AppConfig,
    pub redis: RedisService,
    pub vector_store: VectorStore,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration
    let config = AppConfig::new().expect("Failed to load configuration");
    tracing::info!("Configuration loaded. Redis URL: {}", config.redis_url);

    // Initialize Services
    let redis_service = RedisService::new(&config).await?;
    let vector_store = VectorStore::new(redis_service.clone(), config.clone());
    tracing::info!("Redis and Vector store initialized");

    let state = AppState {
        config: config.clone(),
        redis: redis_service.clone(),
        vector_store: vector_store.clone(),
    };

    // Start Memory Worker (Background Task)
    if state.config.async_memory {
        let worker_state = state.clone();
        tokio::spawn(async move {
            tracing::info!("Starting Memory Worker...");
            if let Err(e) = workers::memory::run_worker(worker_state).await {
                tracing::error!("Memory Worker failed: {:?}", e);
            }
        });
    }

    // Build Router
    let app = Router::new()
        .route("/health", get(routes::health::health_check))
        .route("/config", get(routes::config::get_config))
        .route("/metrics/current", get(routes::metrics::get_metrics))
        .route("/chat", axum::routing::post(routes::chat::chat_handler))
        .with_state(state);

    // Run Server
    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    tracing::info!("Brain (Rust) listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
