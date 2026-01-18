use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::{LLMEngine, EngineRequest};
use std::env;
use std::time::{Duration, Instant};
use tokio::sync::mpsc;

#[derive(Debug)]
struct BenchmarkResult {
    prompt_tokens: usize,
    total_tokens_generated: usize,
    total_duration: Duration,
    time_to_first_token: Duration,
    tokens_per_second: f64,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let args: Vec<String> = env::args().collect();
    let model_name = if args.len() > 1 { &args[1] } else { "TinyLlama/TinyLlama-1.1B-Chat-v1.0" };

    // Resolve model path (use cached version if available)
    let model_path = if std::path::Path::new(model_name).exists() {
        model_name.to_string()
    } else {
        let cache_dir = std::env::var("HF_HOME")
            .ok()
            .map(|p| std::path::PathBuf::from(p))
            .unwrap_or_else(|| std::path::PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/home".to_string())).join(".cache/huggingface/hub"));
        let model_cache_dir = cache_dir.join(format!("models--{}", model_name.replace('/', "--")));
        model_cache_dir.to_str().unwrap_or(model_name).to_string()
    };

    println!("\n🚀 Bolt-XL CPU Mode Benchmark");
    println!("=========================================\n");

    if model_path == "dummy" || model_path == "dummy_model" {
        println!("Generating dummy model at 'dummy_model'...");
        generate_dummy_model("dummy_model").await?;
    } else if !std::path::Path::new(&model_path).exists() {
        println!("Model path not found: {}", model_path);
        println!("Model will be downloaded when running the main binary.");
        return Ok(());
    }

    println!("📦 Model: {}", model_path);
    println!("\n📋 Configuration:");
    println!("  - Warmup steps: 10");
    println!("  - Benchmark steps: 50");
    println!("  - Prompt: \"Write a long story about the history of physics, starting from Newton.\"");
    println!("\n⏱ Warming up...\n");

    let config = Config::default();
    let engine = LLMEngine::new(config, model_path).await?;

    let prompt = "Write a long story about the history of physics, starting from Newton.";

    let (tx, mut rx) = mpsc::unbounded_channel();
    let req = EngineRequest {
        prompt: prompt.to_string(),
        response_tx: tx,
    };

    let req_id = engine.add_request(req).await?;
    println!("  Request ID: {}", req_id);

    for i in 0..10 {
        let _ = engine.step().await?;
        while let Ok(_) = rx.try_recv() {}
    }

    println!("\n📊 Running benchmark...\n");

    let start_time = Instant::now();
    let mut first_token_time: Option<Instant> = None;

    for i in 0..50 {
        let step_start = Instant::now();
        let _ = engine.step().await?;

        while let Ok(token_str) = rx.try_recv() {
            if first_token_time.is_none() {
                first_token_time = Some(step_start);
                let _lat = step_start.elapsed();
            }
        }

        if (i + 1) % 10 == 0 {
            print!("█");
            std::io::stdout().flush().ok();
        }
    }

    let total_duration = start_time.elapsed();
    let time_to_first_token = first_token_time.map(|t| t.duration_since(start_time)).unwrap_or(Duration::ZERO);

    println!("\n📈 Benchmark Results");
    println!("===================\n");
    println!("⏱ Latency Metrics:");
    println!("  Time to first token: {:.2} ms", time_to_first_token.as_secs_f64() * 1000.0);
    println!("  Average token time:  {:.2} ms", total_duration.as_secs_f64() * 1000.0 / 50.0);
    println!("\n📊 Throughput Metrics:");
    println!("  Total tokens: 50");
    println!("  Total duration: {:.2} s", total_duration.as_secs_f64());
    println!("  Tokens/second: {:.2}", 50.0 / total_duration.as_secs_f64());

    Ok(())
}

async fn generate_dummy_model(path: &str) -> anyhow::Result<()> {
    use std::fs;
    use std::path::Path;

    if Path::new(path).exists() {
        return Ok(());
    }

    println!("Generating dummy model at {}...", path);
    fs::create_dir_all(path)?;

    let config_json = serde_json::json!({
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 4096,
        "intermediate_size": 11008,
        "num_attention_heads": 32,
        "num_hidden_layers": 2,
        "num_key_value_heads": 32,
        "vocab_size": 32000,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "tie_word_embeddings": false,
        "quantization_config": {
            "quant_method": "awq",
            "bits": 4,
            "group_size": 128,
            "zero_point": true
        }
    });
    fs::write(format!("{}/config.json", path), serde_json::to_string_pretty(&config_json)?)?;

    let tokenizer = r#"{"model":{"type":"BPE","vocab":{"<unk>":0,"<s>":1,"</s>":2},"merges":[]}"#;
    fs::write(format!("{}/tokenizer.json", path), tokenizer)?;

    println!("Dummy model generated.");
    Ok(())
}
