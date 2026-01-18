use axum::{extract::{State, Json}, response::IntoResponse};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use crate::AppState;
use tracing::{info, error};

#[derive(Deserialize)]
pub struct ChatRequest {
    pub message: String,
    pub model: Option<String>,
}

#[derive(Serialize)]
pub struct ChatResponse {
    pub response: String,
    pub engine: String,
}

pub async fn chat_handler(
    State(state): State<AppState>,
    Json(payload): Json<ChatRequest>,
) -> impl IntoResponse {
    let client = reqwest::Client::new();
    
    // Fallback Logic: Bolt-XL -> Vorpal
    let model = payload.model.unwrap_or_else(|| state.config.vorpal_model.clone());

    let engine_payload = json!({
        "model": model,
        "messages": [
            {"role": "user", "content": payload.message}
        ],
        "max_tokens": state.config.max_tokens,
        "temperature": 0.1,  // Reduced from 0.7 for stability
        "top_p": 0.9         // Added top_p for focus
    });

    // 1. Try Bolt-XL
    let bolt_url = format!("{}/v1/chat/completions", state.config.bolt_xl_url);
    info!("Attempting primary engine: Bolt-XL ({})", bolt_url);

    match call_engine(&client, &bolt_url, &engine_payload).await {
        Ok(content) => {
            return Json(ChatResponse {
                response: content,
                engine: "bolt-xl".to_string(),
            });
        },
        Err(e) => {
            error!("Bolt-XL failed: {}. Falling back to Vorpal.", e);
        }
    }

    // 2. Fallback to Vorpal
    let vorpal_url = format!("{}/v1/chat/completions", state.config.vorpal_url);
    info!("Attempting fallback engine: Vorpal ({})", vorpal_url);

    match call_engine(&client, &vorpal_url, &engine_payload).await {
        Ok(content) => {
            Json(ChatResponse {
                response: content,
                engine: "vorpal".to_string(),
            })
        },
        Err(e) => {
            error!("Vorpal failed: {}.", e);
            Json(ChatResponse {
                response: "All engines failed.".to_string(),
                engine: "error".to_string(),
            })
        }
    }
}

async fn call_engine(client: &reqwest::Client, url: &str, payload: &Value) -> Result<String, String> {
    let res = client.post(url)
        .json(payload)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if res.status().is_success() {
        let body: Value = res.json().await.unwrap_or(json!({}));
        let content = body["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or("Error parsing response")
            .to_string();
        Ok(content)
    } else {
        Err(format!("Engine error: {}", res.status()))
    }
}
