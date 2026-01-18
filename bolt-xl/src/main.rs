use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::LLMEngine;
use clap::{Parser, ValueEnum};

#[derive(ValueEnum, Debug, Clone)]
enum Device {
    Cpu,
    Cuda,
}

#[derive(Parser, Debug)]
#[command(name = "bolt-xl")]
#[command(version = "0.2.0")]
struct Args {
    #[arg(default_value = "TinyLlama/TinyLlama-1.1B-Chat-v1.0")]
    model: String,
    #[arg(short, long, value_enum)]
    device: Option<Device>,
    #[arg(short, long, default_value = "3000")]
    port: u16,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    let mut args = Args::parse();

    // Respect Environment Variable for Model
    if let Ok(env_model) = std::env::var("BOLT_MODEL") {
        tracing::info!("Overriding model from environment: {}", env_model);
        args.model = env_model;
    }

    if let Some(Device::Cpu) = args.device {
        std::env::set_var("BOLT_USE_CPU", "1");
    }

    tracing::info!("Starting Bolt-XL v0.2.0 (Refactored)");
    let config = Config::default();

    match LLMEngine::new(config, &args.model).await {
        Ok(engine) => {
            let engine = std::sync::Arc::new(engine);
            let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel::<bolt_xl::engine::llm_engine::EngineRequest>();

            let engine_clone = engine.clone();
            tokio::spawn(async move {
                while let Some(req) = rx.recv().await {
                    if let Err(e) = engine_clone.add_request(req).await {
                        tracing::error!("Error adding request: {}", e);
                    }
                }
            });

            let engine_clone = engine.clone();
            tokio::spawn(async move {
                loop {
                    if let Err(e) = engine_clone.step().await {
                        tracing::error!("Engine step error: {}", e);
                    }
                    tokio::task::yield_now().await;
                }
            });

            bolt_xl::server::start_server(tx, args.port, args.model).await?;
        },
        Err(e) => {
            tracing::error!("Fatal: {}", e);
            std::process::exit(1);
        }
    }
    Ok(())
}