use notify::{Watcher, RecursiveMode};
use std::path::Path;
use shared::AppConfig;
use tracing::{info, error};
use tokio::sync::mpsc;

mod watcher;
mod processor;

#[derive(Clone)]
pub struct AppState {
    pub config: AppConfig,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize logging
    tracing_subscriber::fmt::init();

    let config = AppConfig::new().expect("Failed to load config");
    info!("Librarian (Rust) started.");

    let state = AppState { config };

    // Channel for file events
    let (tx, mut rx) = mpsc::channel(100);

    // Setup Watcher
    let mut watcher = notify::recommended_watcher(move |res| {
        match res {
            Ok(event) => {
                let _ = tx.blocking_send(event);
            },
            Err(e) => error!("Watch error: {:?}", e),
        }
    })?;

    // Watch directory
    let watch_path = Path::new("/watch");
    if !watch_path.exists() {
        std::fs::create_dir_all(watch_path)?;
    }
    
    watcher.watch(watch_path, RecursiveMode::Recursive)?;
    info!("Watching directory: {:?}", watch_path);

    // Event Loop
    while let Some(event) = rx.recv().await {
        let loop_state = state.clone();
        tokio::spawn(async move {
            if let Err(e) = processor::handle_event(loop_state, event).await {
                error!("Processing error: {:?}", e);
            }
        });
    }

    Ok(())
}
