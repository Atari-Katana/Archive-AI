use axum::{
    extract::{State, Json},
    response::{sse::{Event, Sse}, IntoResponse},
    routing::{get, post},
    Router,
    Json as ResponseJson,
};
use axum::http::StatusCode;
use serde::{Deserialize, Serialize};
use std::convert::Infallible;
use tower_http::cors::CorsLayer;
use tower_http::services::ServeDir;
use tokio::sync::mpsc::UnboundedSender;

use crate::engine::llm_engine::EngineRequest;

#[derive(Clone)]
pub struct AppState {
    pub engine_tx: UnboundedSender<EngineRequest>,
    pub model_name: String,
}

#[derive(Deserialize)]
pub struct ChatCompletionRequest {
    pub messages: Vec<ChatMessage>,
    pub model: Option<String>,
    pub stream: Option<bool>,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

pub async fn start_server(engine_tx: UnboundedSender<EngineRequest>, port: u16, model_name: String) -> anyhow::Result<()> {
    let state = AppState { engine_tx, model_name };

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/v1/models", get(list_models))
        .route("/v1/chat/completions", post(chat_completions))
        .nest_service("/", ServeDir::new("static"))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    tracing::info!("Web UI running at: http://localhost:{}", port);
    
    let listener = tokio::net::TcpListener::bind(&addr).await
        .map_err(|e| anyhow::anyhow!("Failed to bind to {}: {}", addr, e))?;
    axum::serve(listener, app).await
        .map_err(|e| anyhow::anyhow!("Server error: {}", e))?;

    Ok(())
}

/// Health check endpoint
async fn health_check() -> impl IntoResponse {
    tracing::debug!("Health check ping received");
    StatusCode::OK
}

async fn list_models(State(state): State<AppState>) -> impl IntoResponse {
    let response = serde_json::json!({
        "object": "list",
        "data": [{
            "id": state.model_name,
            "object": "model",
            "created": 0,
            "owned_by": "user"
        }]
    });
    ResponseJson(response).into_response()
}

async fn chat_completions(
    State(state): State<AppState>,
    Json(request): Json<ChatCompletionRequest>,
) -> impl IntoResponse {
    // 1. Apply Chat Template
    let prompt = apply_chat_template(&request.messages, &state.model_name);
    tracing::info!("Prompt: {:?}", prompt);

    let should_stream = request.stream.unwrap_or(false);
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();

    let req = EngineRequest {
        prompt,
        response_tx: tx,
    };

    if state.engine_tx.send(req).is_err() {
        return (StatusCode::SERVICE_UNAVAILABLE, ResponseJson(serde_json::json!({"error": "Engine overload"}))).into_response();
    }

    if !should_stream {
        let mut full_response = String::new();
        while let Some(token) = rx.recv().await {
            full_response.push_str(&token);
        }
        
        let response = serde_json::json!({
            "choices": [{
                "message": { "role": "assistant", "content": full_response },
                "finish_reason": "stop"
            }]
        });
        return ResponseJson(response).into_response();
    }

    let stream = async_stream::stream! {
        while let Some(token) = rx.recv().await {
            let json = serde_json::json!({
                "choices": [{
                    "delta": { "content": token }
                }]
            });
            yield Ok::<Event, Infallible>(Event::default().data(json.to_string()));
        }
        let done = serde_json::json!({ "choices": [{ "finish_reason": "stop" }] });
         yield Ok::<Event, Infallible>(Event::default().data(done.to_string()));
    };

    Sse::new(stream)
        .keep_alive(axum::response::sse::KeepAlive::default())
        .into_response()
}

fn apply_chat_template(messages: &[ChatMessage], model_name: &str) -> String {
    let mut prompt = String::new();
    let lower_name = model_name.to_lowercase();

    if lower_name.contains("mistral") {
        // Mistral [INST] format
        let mut first = true;
        for msg in messages {
            if msg.role == "system" {
                prompt.push_str(&format!("{} \n", msg.content));
            } else if msg.role == "user" {
                if first {
                    prompt.push_str(&format!("[INST] {} [/INST]", msg.content));
                    first = false;
                } else {
                    prompt.push_str(&format!("[INST] {} [/INST]", msg.content));
                }
            } else if msg.role == "assistant" {
                prompt.push_str(&format!("{}</s>", msg.content));
            }
        }
    } else if lower_name.contains("tinyllama") || lower_name.contains("zephyr") {
        // Zephyr / TinyLlama format
        for msg in messages {
            match msg.role.as_str() {
                "system" => prompt.push_str(&format!("<|system|>
{}</s>\n", msg.content)),
                "user" => prompt.push_str(&format!("<|user|>
{}</s>\n", msg.content)),
                "assistant" => prompt.push_str(&format!("<|assistant|>
{}</s>\n", msg.content)),
                _ => {}
            }
        }
        prompt.push_str("<|assistant|>
");
    } else {
        // ChatML Default
        for msg in messages {
            prompt.push_str(&format!("<|im_start|>{}\n{}<|im_end|>
", msg.role, msg.content));
        }
        prompt.push_str("<|im_start|>assistant
");
    }
    prompt
}