use crate::AppState;
use anyhow::Result;
use redis::AsyncCommands;
use tracing::{info, warn, error};
use serde_json::json;
use crate::services::memory::SurpriseScorer;
use crate::services::vector_store::VectorStore;

pub async fn run_worker(state: AppState) -> Result<()> {
    let vector_store = VectorStore::new(state.redis.clone(), state.config.clone());
    let scorer = SurpriseScorer::new(vector_store.clone(), state.config.clone());
    
    // Ensure index exists
    if let Err(e) = vector_store.create_index().await {
        warn!("Failed to create/verify index: {:?}", e);
    }

    let mut conn: redis::aio::Connection = state.redis.get_connection().await?;
    let stream_key = &state.config.redis_stream_key;
    let group = "brain_group_rs";
    let consumer = "worker_rs_1";

    // Create consumer group if not exists
    let _: Result<(), _> = redis::cmd("XGROUP")
        .arg("CREATE")
        .arg(stream_key)
        .arg(group)
        .arg("$")
        .arg("MKSTREAM")
        .query_async(&mut conn)
        .await;

    info!("Memory worker (Rust) started. Listening on {}...", stream_key);

    loop {
        // XREADGROUP GROUP brain_group_rs worker_rs_1 COUNT 1 BLOCK 2000 STREAMS session:input_stream >
        let entries: redis::Value = redis::cmd("XREADGROUP")
            .arg("GROUP").arg(group).arg(consumer)
            .arg("COUNT").arg("1")
            .arg("BLOCK").arg("2000")
            .arg("STREAMS").arg(stream_key).arg(">")
            .query_async(&mut conn)
            .await?;

        // Parse stream entries
        if let redis::Value::Bulk(streams) = entries {
            for stream in streams {
                if let redis::Value::Bulk(entries_list) = stream {
                    // entries_list[0] is stream name, entries_list[1] is entries
                    if entries_list.len() < 2 { continue; }
                    if let redis::Value::Bulk(msg_list) = &entries_list[1] {
                        for msg in msg_list {
                            if let redis::Value::Bulk(msg_data) = msg {
                                // msg_data[0] is entry ID, msg_data[1] is field-value pairs
                                let entry_id = match &msg_data[0] {
                                    redis::Value::Data(d) => String::from_utf8_lossy(d).to_string(),
                                    _ => continue,
                                };
                                
                                let mut message = String::new();
                                if let redis::Value::Bulk(fields) = &msg_data[1] {
                                    for i in (0..fields.len()).step_by(2) {
                                        if let (redis::Value::Data(k), redis::Value::Data(v)) = (&fields[i], &fields[i+1]) {
                                            if String::from_utf8_lossy(k) == "message" {
                                                message = String::from_utf8_lossy(v).to_string();
                                            }
                                        }
                                    }
                                }

                                if !message.is_empty() {
                                    info!("Processing stream entry: {}", entry_id);
                                    match scorer.calculate_score(&message).await {
                                        Ok((score, perplexity, distance)) => {
                                            info!("Surprise score: {:.3} (Perplexity: {:.2}, Distance: {:.3})", score, perplexity, distance);
                                            
                                            if score >= state.config.surprise_threshold {
                                                let metadata = json!({
                                                    "source": "rust-worker",
                                                    "entry_id": entry_id,
                                                    "distance": distance
                                                });
                                                if let Err(e) = vector_store.store_memory(&message, perplexity, score, "default", metadata).await {
                                                    error!("Failed to store memory: {:?}", e);
                                                } else {
                                                    info!("Stored surprising memory.");
                                                }
                                            } else {
                                                info!("Skipping (below threshold).");
                                            }
                                        },
                                        Err(e) => error!("Failed to calculate score: {:?}", e),
                                    }
                                }

                                // Acknowledge message
                                let _: () = conn.xack(stream_key, group, &[&entry_id]).await?;
                            }
                        }
                    }
                }
            }
        }
    }
}
