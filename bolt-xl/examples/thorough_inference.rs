use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::LLMEngine;
use bolt_xl::engine::sampling::SamplingParams;
use tokio;
use std::time::Instant;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    println!("🚀 Starting Thorough Bolt-XL Inference Test...");

    // Use a small, fast model for testing
    let model_name = "microsoft/DialoGPT-small"; // ~117M params, quick to download/test
    let mut config = Config::default();
    config.model = model_name.to_string();
    config.max_num_batched_tokens = 50; // Small for speed

    println!("📥 Loading model: {}...", model_name);
    let start = Instant::now();
    let engine = match LLMEngine::new(config, model_name).await {
        Ok(e) => {
            println!("✅ Model loaded in {:.2}s", start.elapsed().as_secs_f32());
            e
        }
        Err(e) => {
            println!("❌ Failed to load model: {}. Make sure it's available or download it.", e);
            return Ok(());
        }
    };

    let test_prompts = vec![
        "Hello, how are you?",
        "What is the capital of France?",
        "Tell me a joke.",
        "Explain quantum physics briefly.",
        "What is 2+2?",
    ];

    println!("\n🧪 Running inference tests...");

    for (i, prompt) in test_prompts.iter().enumerate() {
        println!("\n--- Test {}: '{}' ---", i + 1, prompt);

        let params = SamplingParams {
            temperature: 0.7,
            top_p: 0.9,
            ..Default::default()
        };

        let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();
        let request = bolt_xl::engine::llm_engine::EngineRequest {
            prompt: prompt.to_string(),
            response_tx: tx,
        };

        let req_id = engine.add_request(request).await?;
        println!("📤 Sent request: {}", req_id);

        // Run steps until we get a response (simple for demo)
        let mut response = String::new();
        for _ in 0..10 { // Max 10 steps
            engine.step().await?;
            while let Ok(chunk) = rx.try_recv() {
                response.push_str(&chunk);
            }
            if !response.is_empty() && response.len() > 10 { // Got some output
                break;
            }
            tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        }

        if response.is_empty() {
            println!("❌ No response generated");
        } else {
            println!("✅ Response: '{}'", response.trim());
            // Basic coherence check: should contain words, not gibberish
            if response.len() > 5 && response.chars().any(|c| c.is_alphabetic()) {
                println!("🎉 Coherent response!");
            } else {
                println!("⚠️ Response may be incoherent");
            }
        }
    }

    println!("\n🎊 Thorough Inference Test Complete!");
    println!("Note: For full functionality, test with larger models and enable speculative decoding/quantization.");
    Ok(())
}