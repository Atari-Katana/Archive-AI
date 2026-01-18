use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::{LLMEngine, EngineRequest};
use std::env;
use std::time::Duration;
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args: Vec<String> = env::args().collect();
    let model_path = if args.len() > 1 { &args[1] } else { "models/Qwen2.5-7B-Instruct-AWQ" };

    println!("Testing Coherence on: {}", model_path);
    
    let config = Config::default();
    let mut engine = LLMEngine::new(config, model_path).await?;
    
    let (tx, _rx) = mpsc::unbounded_channel();
    let req = EngineRequest {
        prompt: "Write a short poem about the rust programming language.".to_string(),
        response_tx: tx,
    };
    
    engine.add_request(req).await;

    println!("Generating...");
    for _ in 0..50 {
        engine.step().await?;
    }
    println!("\nDone.");
    Ok(())
}
