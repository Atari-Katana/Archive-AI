use bolt_xl::config::Config;
use bolt_xl::engine::llm_engine::{LLMEngine, EngineRequest};
use std::env;
use std::time::Instant;
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // 1. Parse Args
    let args: Vec<String> = env::args().collect();
    let model_path = if args.len() > 1 {
        &args[1]
    } else {
        "dummy_model"
    };

    if model_path == "dummy" || model_path == "dummy_model" {
        generate_dummy_model("dummy_model").await?;
    } else if !std::path::Path::new(model_path).exists() {
        tracing::warn!("Model path not found locally: {}", model_path);
        tracing::info!("Attempting to generate dummy model at 'dummy_model' instead for benchmark...");
        generate_dummy_model("dummy_model").await?;
        // Update path to dummy
    }
    
    // If we fell back to dummy, use it
    let effective_path = if !std::path::Path::new(model_path).exists() {
        "dummy_model"
    } else {
        model_path
    };

    tracing::info!("Starting Benchmark on model: {}", effective_path);
    tracing::info!("Target: {} iterations", iterations);

    // 2. Initialize Engine
    let config = Config::default();
    let mut engine = LLMEngine::new(config, effective_path).await?;
    
    // 3. Add Request
    let (tx, mut rx) = mpsc::unbounded_channel();
    let req = EngineRequest {
        prompt: "Write a long story about the history of physics, starting from Newton.".to_string(),
        response_tx: tx,
    };
    
    let req_id = engine.add_request(req).await?;
    tracing::info!("Request added: {}", req_id);

    // 4. Warmup
    tracing::info!("Warming up (10 steps)...");
    for _ in 0..10 {
        engine.step().await?;
        // Drain output
        while let Ok(_) = rx.try_recv() {}
    }

    // 5. Benchmark Loop
    println!("Starting measurement...");
    let start_time = Instant::now();
    let iterations = 10;
    
    for i in 0..iterations {
        engine.step().await?;
        
        // Drain output to prevent channel backpressure (if bounded)
        // Check if finished? 
        // Our engine step doesn't return "finished" status easily here unless we check scheduler.
        // But for benchmark, we just want to run N steps.
        // If generation finishes early, step() might return Ok but do nothing.
        // We should ensure prompt is long enough or ignore finish.
        // "Write a long story..." should suffice.
        
        while let Ok(_) = rx.try_recv() {}
        
        if (i+1) % 100 == 0 {
             print!(".");
             use std::io::Write;
             std::io::stdout().flush().ok();
        }
    }
    tracing::info!("Benchmark Complete.");
    tracing::info!("Total Time: {:.4} s", seconds);
    tracing::info!("Total Tokens: {}", iterations);
    tracing::info!("Throughput: {:.2} tokens/sec", tps);

    Ok(())
}

async fn generate_dummy_model(path: &str) -> anyhow::Result<()> {
    use std::fs;
    use std::path::Path;
    use candle_core::{Tensor, DType, Device};

    use std::collections::HashMap;

    if Path::new(path).exists() {
        return Ok(());
    }

    tracing::info!("Generating dummy model at {}...", path);
    fs::create_dir_all(path)?;

    // 1. Config
    let config_json = serde_json::json!({
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 4096,
        "intermediate_size": 11008,
        "num_attention_heads": 32,
        "num_hidden_layers": 2, // Small for benchmark speed/memory, but enough to verify
        "num_key_value_heads": 32,
        "vocab_size": 32000,
        "rms_norm_eps": 1e-5,
         "rope_theta": 10000.0,
         "max_position_embeddings": 4096,
         "tie_word_embeddings": false,
        "quantization_config": {
            "quant_method": "awq",
            "bits": 4,
            "group_size": 128,
            "zero_point": true,
            "version": "gemm"
        }
    });
    fs::write(format!("{}/config.json", path), serde_json::to_string_pretty(&config_json)?)?;

    // 2. Tokenizer (Minimal)
    fs::write(format!("{}/tokenizer.json", path), r#"{"model":{"type":"BPE","vocab":{"<unk>":0},"merges":[]}}"#)?;

    // 3. Weights
    let device = Device::Cpu;
    let mut tensors = HashMap::new();
    
    // Helper to add tensor
    let mut add = |name: &str, shape: &[usize], dtype: DType| {
        let t = Tensor::zeros(shape, dtype, &device).unwrap();
        // serializing zeros is fast
        t
    };

    // Embeddings
    tensors.insert("model.embed_tokens.weight".to_string(), add("embed", &[32000, 4096], DType::F16));
    
    // Layers
    for i in 0..2 {
        let p = format!("model.layers.{}", i);
        tensors.insert(format!("{}.input_layernorm.weight", p), add("ln", &[4096], DType::F16));
        tensors.insert(format!("{}.post_attention_layernorm.weight", p), add("ln", &[4096], DType::F16));
        
        // Attention (QKV) - Marlin/AWQ requires packed weights. 
        // We use zeros, so packing is trivial (all zeros).
        // Shapes: [Out, In/8] for qweight (U32)
        // Groups: [In/128, Out] for scales (F16)
        
        let hidden = 4096;
        let p_q = |name: &str, out: usize, in_dim: usize, tensors: &mut HashMap<String, Tensor>| {
             tensors.insert(format!("{}.qweight", name), add("q", &[in_dim / 8, out], DType::U32)); // Transposed?
             // AWQLinear loads: (in_features, out_features / 8)
             // Check quantization.rs:
             // let qweight = vb_int.get((in_features, out_features / 8), "qweight")?;
             
             // Wait, usually weights are names like `q_proj.qweight`.
             // `q_proj` is (In, Out).
             // qweight shape in `load` is `(In, Out/8)`.
             // So we create (4096, 4096/8) -> (4096, 512).
             
             tensors.insert(format!("{}.qweight", name), add("q", &[in_dim, out / 8], DType::U32));
             tensors.insert(format!("{}.qzeros", name), add("z", &[in_dim / 128, out / 8], DType::U32));
             tensors.insert(format!("{}.scales", name), add("s", &[in_dim / 128, out], DType::F16));
        };

        p_q(&format!("{}.self_attn.q_proj", p), 4096, 4096, &mut tensors);
        p_q(&format!("{}.self_attn.k_proj", p), 4096, 4096, &mut tensors);
        p_q(&format!("{}.self_attn.v_proj", p), 4096, 4096, &mut tensors);
        p_q(&format!("{}.self_attn.o_proj", p), 4096, 4096, &mut tensors);
        
        // MLP (Gate/Up/Down)
        let inter = 11008;
        p_q(&format!("{}.mlp.gate_proj", p), inter, 4096, &mut tensors);
        p_q(&format!("{}.mlp.up_proj", p), inter, 4096, &mut tensors);
        p_q(&format!("{}.mlp.down_proj", p), 4096, inter, &mut tensors);
    }
    
    tensors.insert("model.norm.weight".to_string(), add("norm", &[4096], DType::F16));
    tensors.insert("lm_head.weight".to_string(), add("lm", &[32000, 4096], DType::F16));

    candle_core::safetensors::save(&tensors, format!("{}/model.safetensors", path))?;
    
    tracing::info!("Dummy model generated.");
    Ok(())
}
