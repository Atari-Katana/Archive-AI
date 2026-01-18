use notify::Event;
use anyhow::Result;
use tracing::{info, error};
use std::fs;
use crate::AppState;

pub async fn handle_event(state: AppState, event: Event) -> Result<()> {
    // We only care about file creation or modification
    if event.kind.is_create() || event.kind.is_modify() {
        for path in event.paths {
            if path.is_file() {
                // Filter for supported extensions
                let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
                if ext == "txt" || ext == "md" {
                    info!("Processing file: {:?}", path);
                    if let Err(e) = process_file(&state, &path).await {
                        error!("Failed to process {:?}: {:?}", path, e);
                    }
                }
            }
        }
    }
    Ok(())
}

async fn process_file(state: &AppState, path: &std::path::Path) -> Result<()> {
    let content = fs::read_to_string(path)?;
    let filename = path.file_name().and_then(|s| s.to_str()).unwrap_or("unknown");
    
    // Simple recursive chunker (mocked for now)
    // In real app, would use semantic chunking
    let chunks = chunk_text(&content, 500);
    
    info!("Split {} into {} chunks", filename, chunks.len());
    
    for (i, chunk) in chunks.iter().enumerate() {
        let _metadata = serde_json::json!({
            "filename": filename,
            "chunk_index": i,
            "type": "library"
        });
        
        // Push to Redis (Mocked logic)
        // state.vector_store.store_memory(chunk, 0.0, 0.0, "library", metadata).await?;
    }
    
    Ok(())
}

fn chunk_text(text: &str, size: usize) -> Vec<String> {
    let mut chunks = Vec::new();
    let words: Vec<&str> = text.split_whitespace().collect();
    
    for chunk in words.chunks(size) {
        chunks.push(chunk.join(" "));
    }
    
    chunks
}