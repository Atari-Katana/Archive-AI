use axum::{extract::State, Json};
use serde_json::{json, Value};
use crate::AppState;

pub async fn health_check(State(_state): State<AppState>) -> Json<Value> {
    Json(json!({
        "status": "healthy",
        "service": "brain-rs",
        "version": env!("CARGO_PKG_VERSION")
    }))
}
