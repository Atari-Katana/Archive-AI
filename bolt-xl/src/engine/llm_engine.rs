use std::sync::{Arc, atomic::{AtomicU64, Ordering}};
use tokio::sync::Mutex as TokioMutex;
use candle_core::{Device, DType};

use crate::config::Config;
use crate::engine::scheduler::Scheduler;
use crate::engine::model_executor::ModelExecutor;
use crate::engine::sequence::{Sequence, SequenceGroup, SequenceStatus};
use crate::engine::sampling::{Sampler, SamplingParams};

pub struct EngineRequest {
    pub prompt: String,
    pub response_tx: tokio::sync::mpsc::UnboundedSender<String>,
}

pub struct LLMEngine {
    pub scheduler: Arc<TokioMutex<Scheduler>>,
    pub model_executor: Arc<ModelExecutor>,
    pub sampler: TokioMutex<Sampler>,
    pub tokenizer: tokenizers::Tokenizer,
    pub request_counter: Arc<AtomicU64>,
}

impl LLMEngine {
    pub async fn new(config: Config, model_name: &str) -> anyhow::Result<Self> {
        config.validate().map_err(anyhow::Error::msg)?;
        
        let (device, dtype) = if std::env::var("BOLT_USE_CPU").is_ok() {
            tracing::info!("LLMEngine: Using CPU device (float32).");
            (Device::Cpu, DType::F32)
        } else {
             // Try CUDA, fallback to CPU handled by candle? No, we must be explicit.
             match Device::new_cuda(0) {
                 Ok(d) => (d, DType::F16),
                 Err(e) => {
                     tracing::warn!("Failed to initialize CUDA: {}. Fallback to CPU.", e);
                     (Device::Cpu, DType::F32)
                 }
             }
        };

        let model_executor = Arc::new(ModelExecutor::new(config.clone(), model_name, device, dtype)?);
        let scheduler = Arc::new(TokioMutex::new(Scheduler::new(config.clone())));
        let sampler = TokioMutex::new(Sampler::new(42));
        
        // Load tokenizer
        let model_path = std::path::Path::new(model_name);
        let tokenizer_path = if model_path.exists() {
             model_path.join("tokenizer.json")
        } else {
             // Assuming cache dir structure from executor logic, but simpliest is to assume it's downloaded
             // The executor already downloaded it? No, executor logic was separate.
             // We need to resolve path again or rely on executor. 
             // Ideally we pass the path.
             // For now, assume generic load or fail.
             // Correction: Executor downloads if missing. We should use `hf-hub` or similar here too.
             // Let's rely on the file existing now because executor ran `new` first.
             let cache_dir = std::env::var("HF_HOME")
                .ok()
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::path::PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/home".to_string())).join(".cache/huggingface/hub"));
            let model_cache_dir = cache_dir.join(format!("models--{}", model_name.replace('/', "--")));
            model_cache_dir.join("tokenizer.json")
        };
        
        let tokenizer = tokenizers::Tokenizer::from_file(&tokenizer_path)
            .map_err(|e| anyhow::anyhow!("Failed to load tokenizer from {:?}: {}", tokenizer_path, e))?;

        Ok(Self {
            scheduler,
            model_executor,
            sampler,
            tokenizer,
            request_counter: Arc::new(AtomicU64::new(0)),
        })
    }
    
    pub async fn add_request(&self, request: EngineRequest) -> anyhow::Result<String> {
        let counter = self.request_counter.fetch_add(1, Ordering::SeqCst);
        let req_id = format!("req_{}", counter);
        
        let prompt = request.prompt;
        let encoding = self.tokenizer.encode(prompt.clone(), true).map_err(|e| anyhow::anyhow!("Tokenizer error: {}", e))?;
        let token_ids = encoding.get_ids().to_vec();

        let seq = Sequence::new(counter, prompt, token_ids, Some(request.response_tx));
        let sg = SequenceGroup::new(req_id.clone(), vec![seq]);

        let mut scheduler = self.scheduler.lock().await;
        scheduler.add_request(sg)?;
        
        Ok(req_id)
    }

    pub async fn step(&self) -> anyhow::Result<()> {
        let mut scheduler = self.scheduler.lock().await;
        let batch = scheduler.step();
        drop(scheduler);

        if batch.seq_groups.is_empty() {
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
            return Ok(());
        }
        
        // Run Model
        let logits = self.model_executor.run(&batch)?; 
        // Logits: [BatchSize, 1, Vocab]

        let mut sampler = self.sampler.lock().await;
        
        // Iterate over batch results
        // Note: run() guarantees order matches batch.seq_groups
        let (b_size, _seq, _vocab) = logits.dims3()?;
        assert_eq!(b_size, batch.seq_groups.len());

        // We need to update the scheduler's running sequences
        let mut scheduler = self.scheduler.lock().await;
        
        for (i, sg_out) in batch.seq_groups.iter().enumerate() {
            let logit = logits.get(i)?; // [1, Vocab]
            let next_token = sampler.sample(&logit, &SamplingParams::default())?; // Sample returns u32

            // Find the sequence in scheduler to update
            if let Some(sg_ref) = scheduler.running_mut().iter_mut().find(|g| g.request_id == sg_out.request_id) {
                if let Some(seq) = sg_ref.seqs.first_mut() {
                    seq.append_token_id(next_token);
                    
                    // Check Stop Conditions (EOS)
                    let eos_token = self.tokenizer.token_to_id("</s>").or_else(|| self.tokenizer.token_to_id("<|endoftext|>"));
                    if Some(next_token) == eos_token {
                         seq.set_status(SequenceStatus::Finished);
                    }

                    // Decode delta
                    let full_text = self.tokenizer.decode(&seq.output_token_ids, true).unwrap_or_default();
                    let new_text = full_text[seq.output_text.len()..].to_string();
                    seq.output_text = full_text;

                    if !new_text.is_empty() {
                         if let Some(tx) = &seq.sender {
                             let _ = tx.send(new_text);
                         }
                    }
                    
                    // Close channel if finished
                    if seq.is_finished() {
                         // Drop sender to close channel
                         seq.sender = None;
                    }
                }
            }
        }
        
        Ok(())
    }
}
