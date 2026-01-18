use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::{LLMEngine, EngineRequest};
use std::env;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::mpsc;

#[derive(Debug)]
struct BenchmarkResult {
    prompt_tokens: usize,
    total_tokens_generated: usize,
    total_duration: Duration,
    time_to_first_token: Duration,
    tokens_per_second: f64,
    p50_latency_ms: f64,
    p90_latency_ms: f64,
    p99_latency_ms: f64,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let args: Vec<String> = env::args().collect();
    let model_path = if args.len() > 1 { &args[1] } else { "dummy_model" };

    println!("\n🚀 Bolt-XL Inference Benchmark");
    println!("=========================================\n");

    if model_path == "dummy" || model_path == "dummy_model" {
        println!("Generating dummy model at 'dummy_model'...");
        generate_dummy_model("dummy_model").await?;
    } else if !std::path::Path::new(model_path).exists() {
        tracing::warn!("Model path not found: {}", model_path);
        println!("Model path not found: {}", model_path);
        return Ok(());
    }

    let effective_path = if !std::path::Path::new(model_path).exists() {
        "dummy_model"
    } else {
        model_path
    };

    println!("📦 Model: {}", effective_path);
    println!("\n📋 Configuration:");
    println!("  - Warmup steps: 10");
    println!("  - Benchmark steps: 50");
    println!("  - Tokens per step: 1");
    println!("  - Prompt: \"Write a long story about the history of physics, starting from Newton.\"\n");

    let config = Config::default();
    let engine = Arc::new(LLMEngine::new(config, effective_path).await?);

    let prompt = "Write a long story about the history of physics, starting from Newton.";

    let (tx, mut rx) = mpsc::unbounded_channel();
    let req = EngineRequest {
        prompt: prompt.to_string(),
        response_tx: tx,
    };

    let req_id = engine.add_request(req).await?;
    println!("  Request ID: {}", req_id);
    println!("\n⏱ Warming up...\n");

    for i in 0..10 {
        let _ = engine.step().await?;
        while let Ok(_) = rx.try_recv() {}

        if (i + 1) % 5 == 0 {
            print!(".");
            std::io::stdout().flush().ok();
        }
    }
    println!();

    println!("\n📊 Running benchmark...\n");

    let mut latencies = Vec::with_capacity(50);

    let start_time = Instant::now();
    let mut first_token_time: Option<Instant> = None;

    for i in 0..50 {
        let step_start = Instant::now();
        let _ = engine.step().await?;

        while let Ok(token_str) = rx.try_recv() {
            if first_token_time.is_none() {
                first_token_time = Some(step_start);
                let latency = step_start.elapsed();
                latencies.push(latency.as_millis_f64());
            }

            if token_str.len() > 0 {
                latencies.push(step_start.elapsed().as_millis_f64());
            }
        }

        if (i + 1) % 10 == 0 {
            print!("█");
            std::io::stdout().flush().ok();
        }
    }

    println!();
    let total_duration = start_time.elapsed();

    latencies.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let p50_idx = (latencies.len() as f64 * 0.50).floor() as usize;
    let p90_idx = (latencies.len() as f64 * 0.90).floor() as usize;
    let p99_idx = (latencies.len() as f64 * 0.99).floor() as usize;

    let p50 = latencies.get(p50_idx).copied().unwrap_or(0.0);
    let p90 = latencies.get(p90_idx).copied().unwrap_or(0.0);
    let p99 = latencies.get(p99_idx).copied().unwrap_or(0.0);

    let avg_latency = latencies.iter().sum::<f64>() / latencies.len() as f64;

    let time_to_first_token = first_token_time.map(|t| t.duration_since(start_time)).unwrap_or(Duration::ZERO);

    println!("\n📈 Benchmark Results");
    println!("===================\n");

    println!("\n⏱ Latency Metrics:");
    println!("  Time to first token: {:.2} ms", time_to_first_token.as_millis_f64());
    println!("  Average latency:    {:.2} ms", avg_latency);
    println!("  P50 latency:       {:.2} ms", p50);
    println!("  P90 latency:       {:.2} ms", p90);
    println!("  P99 latency:       {:.2} ms", p99);
    println!("  Min latency:       {:.2} ms", latencies.iter().cloned().fold(f64::INFINITY, f64::min));

    println!("\n📊 Throughput Metrics:");
    println!("  Total steps:        {}", latencies.len());
    println!("  Total duration:     {:.2} s", total_duration.as_secs_f64());
    println!("  Tokens/second:     {:.2}", latencies.len() as f64 / total_duration.as_secs_f64());

    println!("\n💾 System Info:");
    if let Ok(mem_info) = sys_info::mem_info() {
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
    use std::path::Path;

    pub struct MemInfo {
        pub used: u64,
        pub total: u64,
    }

    pub fn mem_info() -> Result<MemInfo, ()> {
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

    pub fn uptime() -> Result<Duration, ()> {
        let info = fs::read_to_string("/proc/uptime")?;
        let uptime_secs: f64 = info.split_whitespace()
            .next()
            .and_then(|v| v.parse::<f64>().ok())
            .unwrap_or(0.0);

        Ok(Duration::from_secs_f64(uptime_secs))
    }
}
