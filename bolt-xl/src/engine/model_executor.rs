use candle_core::{Tensor, Device, DType}; 
use candle_nn::VarBuilder;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use ureq::Error as UreqError;

use crate::models::llama::{LlamaForCausalLM, LlamaConfig};
use crate::config::Config;
use crate::engine::scheduler::Batch;

type KVCache = Vec<(Option<Tensor>, Option<Tensor>)>;

pub struct ModelExecutor {
    pub model: LlamaForCausalLM,
    pub device: Device,
    pub config: Config,
    pub cache: Arc<Mutex<HashMap<String, KVCache>>>,
    pub redis_client: Option<redis::Client>,
}

impl ModelExecutor {
    pub fn new(config: Config, model_name: &str, device: Device, dtype: DType) -> anyhow::Result<Self> {
        let redis_client = redis::Client::open("redis://archive-redis:6379").ok();
        
        let report_status = |status: &str| {
            if let Some(client) = &redis_client {
                if let Ok(mut conn) = client.get_connection() {
                    let _: redis::RedisResult<()> = redis::cmd("SET").arg("bolt_xl:loading_status").arg(status).query(&mut conn);
                }
            }
        };

        let device_str = if device.is_cuda() { "GPU (CUDA)" } else { "CPU" };
        if let Some(client) = &redis_client {
            if let Ok(mut conn) = client.get_connection() {
                let _: redis::RedisResult<()> = redis::cmd("SET").arg("bolt_xl:device").arg(device_str).query(&mut conn);
            }
        }

        report_status("Initializing...");

        let mut safetensors_files = Vec::new();
        let model_path = std::path::Path::new(model_name);

        if model_path.exists() {
             tracing::info!("Loading model from local path: {:?}", model_path);
             report_status("Scanning local files...");
             let single_file = model_path.join("model.safetensors");
             if single_file.exists() {
                 safetensors_files.push(single_file);
             } else {
                 match std::fs::read_dir(model_path) {
                     Ok(entries) => {
                         for entry in entries {
                              let entry = entry?;
                              let path = entry.path();
                              if let Some(ext) = path.extension() {
                                  if ext == "safetensors" {
                                      safetensors_files.push(path);
                                  }
                              }
                         }
                     },
                     Err(e) => return Err(anyhow::anyhow!("Failed to read model dir {}: {}", model_name, e)),
                 }
             }
             let config_path = model_path.join("config.json");
             if safetensors_files.is_empty() {
                 return Err(anyhow::anyhow!("No .safetensors files found in {:?}", model_path));
             }
             safetensors_files.sort();
             
             Self::load_from_files_static(config, config_path, safetensors_files, device, dtype, redis_client)
        } else {
            tracing::info!("Model not found locally. Downloading {} from HuggingFace...", model_name);
            report_status("Connecting to HF Hub...");

            let cache_dir = std::env::var("HF_HOME")
                .ok()
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::path::PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/root".to_string())).join(".cache/huggingface/hub"));
            let model_cache_dir = cache_dir.join(format!("models--{}", model_name.replace('/', "--")));
            std::fs::create_dir_all(&model_cache_dir)?;
            let hf_token = std::env::var("HF_TOKEN").ok();

            let download_hf_file = |filename: &str| -> anyhow::Result<std::path::PathBuf> {
                report_status(&format!("Downloading {}...", filename));
                let dest = model_cache_dir.join(filename);
                if dest.exists() {
                    return Ok(dest);
                }
                let url = format!("https://huggingface.co/{}/resolve/main/{}", model_name, filename);
                let mut request = ureq::get(&url);
                if let Some(token) = hf_token.as_ref() {
                    request = request.set("Authorization", &format!("Bearer {}", token));
                }
                let resp = match request.call() {
                    Ok(resp) => resp,
                    Err(UreqError::Status(code, _)) => {
                        return Err(anyhow::anyhow!("download failed for {}: status {}", filename, code));
                    }
                    Err(e) => {
                        return Err(anyhow::anyhow!("download failed for {}: {}", filename, e));
                    }
                };
                let mut reader = resp.into_reader();
                let mut file = std::fs::File::create(&dest)?;
                std::io::copy(&mut reader, &mut file)?;
                Ok(dest)
            };

            let config_path = download_hf_file("config.json")?;
            let _ = download_hf_file("tokenizer.json")?;
            
            match download_hf_file("model.safetensors.index.json") {
                Ok(idx_path) => {
                    let idx_file = std::fs::File::open(&idx_path)?;
                    let index: serde_json::Value = serde_json::from_reader(idx_file)?;
                    let weight_map = index["weight_map"].as_object().ok_or_else(|| anyhow::anyhow!("Invalid index"))?;
                    let mut filenames: Vec<String> = weight_map.values().map(|v| v.as_str().unwrap().to_string()).collect();
                    filenames.sort();
                    filenames.dedup();
                    for f in filenames {
                        safetensors_files.push(download_hf_file(&f)?);
                    }
                },
                Err(_) => {
                    safetensors_files.push(download_hf_file("model.safetensors")?);
                }
            }
            
            safetensors_files.sort();
            Self::load_from_files_static(config, config_path, safetensors_files, device, dtype, redis_client)
        }
    }

    fn load_from_files_static(config: Config, config_path: std::path::PathBuf, safetensors_files: Vec<std::path::PathBuf>, device: Device, dtype: DType, redis_client: Option<redis::Client>) -> anyhow::Result<Self> {
        if let Some(client) = &redis_client {
            if let Ok(mut conn) = client.get_connection() {
                let _: redis::RedisResult<()> = redis::cmd("SET").arg("bolt_xl:loading_status").arg("Mapping weights...").query(&mut conn);
            }
        }
        
        tracing::info!("Loading weights from {:?}...", safetensors_files);
        let vb = unsafe { VarBuilder::from_mmaped_safetensors(&safetensors_files, dtype, &device)? }; 
        let vb_quant = unsafe { VarBuilder::from_mmaped_safetensors(&safetensors_files, DType::U32, &device)? }; 
        
        let config_file = std::fs::File::open(&config_path).map_err(|e| anyhow::anyhow!("Failed to open config.json: {}", e))?;
        let llama_config: LlamaConfig = serde_json::from_reader(config_file).map_err(|e| anyhow::anyhow!("Failed to parse config.json: {}", e))?;
        
        let model = LlamaForCausalLM::load(vb, vb_quant, &llama_config).map_err(|e| anyhow::anyhow!("Load Error: {}", e))?;
        
        if let Some(client) = &redis_client {
            if let Ok(mut conn) = client.get_connection() {
                let _: redis::RedisResult<()> = redis::cmd("SET").arg("bolt_xl:loading_status").arg("Ready").query(&mut conn);
            }
        }

        Ok(Self {
            model,
            device,
            config,
            cache: Arc::new(Mutex::new(HashMap::new())),
            redis_client,
        })
    }

    pub fn run(&self, batch: &Batch) -> anyhow::Result<Tensor> {
        if batch.seq_groups.is_empty() {
             return Ok(Tensor::zeros((1, 1), DType::F32, &self.device)?);
        }

        let mut all_logits = Vec::new();
        let mut cache_guard = self.cache.lock().unwrap();

        for sg in &batch.seq_groups {
            if let Some(seq) = sg.seqs.first() {
                let req_cache = cache_guard.entry(sg.request_id.clone()).or_default();
                
                let (input_ids, pos_ids) = if seq.output_token_ids.is_empty() {
                    let ids = seq.prompt_token_ids.clone();
                    let pos: Vec<u32> = (0..ids.len() as u32).collect();
                    (ids, pos)
                } else {
                    let last_token = *seq.output_token_ids.last()
                        .ok_or_else(|| anyhow::anyhow!("No tokens in output_token_ids"))?;
                    let pos = (seq.prompt_token_ids.len() + seq.output_token_ids.len() - 1) as u32;
                    (vec![last_token], vec![pos])
                };
                
                let input_tensor = Tensor::new(input_ids.as_slice() as &[u32], &self.device)?.unsqueeze(0)?; 
                let pos_tensor = Tensor::new(pos_ids.as_slice() as &[u32], &self.device)?.unsqueeze(0)?;
                
                let logits = self.model.forward(&input_tensor, &pos_tensor, req_cache)?;
                
                let (_b, s, _v) = logits.dims3()?;
                let last_logit = logits.narrow(1, s - 1, 1)?;
                all_logits.push(last_logit);
            }
        }
        
        if all_logits.is_empty() {
            return Ok(Tensor::zeros((1, 1), DType::F32, &self.device)?);
        }
        
        let batch_logits = Tensor::cat(&all_logits, 0)?; 
        Ok(batch_logits)
    }
}
