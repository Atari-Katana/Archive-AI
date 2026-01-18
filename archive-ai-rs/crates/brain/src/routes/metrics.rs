use axum::{extract::{State, Json}, response::IntoResponse};
use serde_json::json;
use crate::AppState;
use redis::AsyncCommands;

pub async fn get_metrics(State(state): State<AppState>) -> impl IntoResponse {
    let mut tps = 0.0;
    
    // Try to read real metrics from Redis
    if let Ok(mut conn) = state.redis.get_connection().await {
        if let Ok(val) = conn.get::<_, f64>("metrics:bolt_xl:tps").await {
            tps = val;
        }
    }
    
    Json(json!({
        "status": "healthy",
        "tokens_per_sec": tps,
        "total_requests": 0 // TODO: Implement request counting
    }))
}