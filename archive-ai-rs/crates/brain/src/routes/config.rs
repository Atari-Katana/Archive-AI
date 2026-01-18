use axum::{extract::{State, Json}, response::IntoResponse};
use serde_json::json;
use crate::AppState;

pub async fn get_config(State(state): State<AppState>) -> impl IntoResponse {
    // Return the current loaded config
    // Note: In a real app, we might want to mask secrets or return a specific DTO
    Json(state.config)
}
