use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::{LLMEngine, EngineRequest};
use std::io::Write;
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

    let args: Vec<String> = std::env::args().collect();
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

    println!("\n🚀 Bolt-XL CPU-Only Inference Test");
    println!("=========================================\n");

    if !std::path::Path::new(&model_path).exists() {
        println!("Model path not found: {}", model_path);
        println!("The model will be downloaded when running the main binary.");
        return Ok(());
    }

    println!("📦 Model: {}", model_path);
    println!("\n📋 Configuration:");
    println!("  - Warmup steps: 5");
    println!("  - Inference steps: 20");
    println!("  - Tokens per step: 1");
    println!("  - Prompt: \"Explain quantum computing in simple terms for a computer science student.\"\n");

    let config = Config::default();

    println!("\n⏱ Initializing engine...");
    let engine = LLMEngine::new(config, model_path).await?;

    let prompt = "Explain quantum computing in simple terms for a computer science student.";
    let (tx, mut rx) = mpsc::unbounded_channel();
    let req = EngineRequest {
        prompt: prompt.to_string(),
        response_tx: tx,
    };

    let req_id = engine.add_request(req).await?;
    println!("Request ID: {}", req_id);

    println!("\n⏱ Warming up...");
    for _ in 0..5 {
        engine.step().await?;
        while let Ok(_) = rx.try_recv() {}
    }

    println!("\n📊 Running inference benchmark...");

    let mut latencies = Vec::with_capacity(20);
    let mut first_token_time: Option<Instant> = None;

    let start_time = Instant::now();

    for i in 0..20 {
        let step_start = Instant::now();
        let _ = engine.step().await?;

        while let Ok(token_str) = rx.try_recv() {
            if first_token_time.is_none() {
                first_token_time = Some(step_start);
                let latency = step_start.elapsed();
                latencies.push(latency.as_secs_f64() * 1000.0);
            }

            if token_str.len() > 0 {
                latencies.push(step_start.elapsed().as_secs_f64() * 1000.0);
            }
        }

        if (i + 1) % 5 == 0 {
            print!("█");
            std::io::stdout().flush().ok();
        }
    }

    let total_duration = start_time.elapsed();

    latencies.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let p50_idx = (latencies.len() as f64 * 0.50).floor() as usize;
    let p90_idx = (latencies.len() as f64 * 0.90).floor() as usize;
    let p95_idx = (latencies.len() as f64 * 0.95).floor() as usize;
    let p99_idx = (latencies.len() as f64 * 0.99).floor() as usize;

    let p50 = latencies.get(p50_idx).copied().unwrap_or(0.0);
    let p90 = latencies.get(p90_idx).copied().unwrap_or(0.0);
    let p95 = latencies.get(p95_idx).copied().unwrap_or(0.0);
    let p99 = latencies.get(p99_idx).copied().unwrap_or(0.0);

    let avg_latency = latencies.iter().sum::<f64>() / latencies.len() as f64;

    let time_to_first_token = first_token_time.map(|t| t.duration_since(start_time)).unwrap_or(Duration::ZERO);

    println!("\n📈 Benchmark Results");
    println!("===================\n");

    println!("\n📊 Latency Metrics:");
    println!("  Time to first token: {:.2} ms", time_to_first_token.as_secs_f64() * 1000.0);
    println!("  Average latency:    {:.2} ms", avg_latency);
    println!("  P50 latency:       {:.2} ms", p50);
    println!("  P90 latency:       {:.2} ms", p90);
    println!("  P95 latency:       {:.2} ms", p95);
    println!("  P99 latency:       {:.2} ms", p99);
    println!("  Min latency:       {:.2} ms", latencies.iter().cloned().fold(f64::INFINITY, f64::min));

    println!("\n📊 Throughput Metrics:");
    println!("  Total steps:        {}", latencies.len());
    println!("  Total duration:     {:.2} s", total_duration.as_secs_f64());
    println!("  Tokens/second:     {:.2}", latencies.len() as f64 / total_duration.as_secs_f64());

    if let Ok(mem_info) = sys_info::mem_info() {
        println!("\n💾 System Info:");
        println!("  Memory used:        {} MB", mem_info.used / 1024 / 1024);
        println!("  Memory total:       {} MB", mem_info.total / 1024 / 1024);
    }

    if let Ok(uptime) = sys_info::uptime() {
        println!("  System uptime:      {}s", uptime.as_secs());
    }

    Ok(())
}

mod sys_info {
    use std::fs;
    use std::time::Duration;

    pub struct MemInfo {
        pub used: u64,
        pub total: u64,
    }

    pub fn mem_info() -> Result<MemInfo, std::io::Error> {
        let info = fs::read_to_string("/proc/meminfo")?;
        let used = info.lines()
            .find(|line| line.starts_with("MemAvailable:"))
            .and_then(|line| line.split_whitespace().nth(1))
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(0);

        let total = info.lines()
            .find(|line| line.starts_with("MemTotal:"))
            .and_then(|line| line.split_whitespace().nth(1))
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(0);

        Ok(MemInfo {
            used: total - used,
            total,
        })
    }

    pub fn uptime() -> Result<Duration, std::io::Error> {
        let info = fs::read_to_string("/proc/uptime")?;
        let uptime_secs: f64 = info.split_whitespace()
            .next()
            .and_then(|v| v.parse::<f64>().ok())
            .unwrap_or(0.0);

        Ok(Duration::from_secs_f64(uptime_secs))
    }
}
