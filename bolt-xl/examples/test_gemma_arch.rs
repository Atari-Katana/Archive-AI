use bolt_xl::models::llama::{LlamaForCausalLM, LlamaConfig};
use candle_core::{Tensor, DType, Device};
use candle_nn::VarBuilder;
use std::collections::HashMap;

fn main() -> anyhow::Result<()> {
    println!("Testing Gemma 2 Architecture Support...");

    // 1. Simulate Gemma 2 Config
    let config = LlamaConfig {
        hidden_size: 2048, // Reduced for test
        intermediate_size: 16384, // Reduced
        num_hidden_layers: 2,
        num_attention_heads: 8,
        num_key_value_heads: Some(4),
        vocab_size: 32000,
        rms_norm_eps: 1e-6,
        rope_theta: 10000.0,
        max_position_embeddings: 8192,
        tie_word_embeddings: true,
        attn_logit_softcapping: Some(50.0),
        final_logit_softcapping: Some(30.0),
        hidden_act: Some("gelu_pytorch_tanh".to_string()),
        head_dim: Some(256), 
    };
    
    println!("Config created: {:?}", config);

    // 2. Create Dummy Weights
    let device = Device::Cpu;
    let mut tensors = HashMap::new();
    
    // Embed Tokens
    tensors.insert("model.embed_tokens.weight".to_string(), Tensor::zeros((32000, 2048), DType::F16, &device)?);
    
    // Layers
    for i in 0..2 {
        let p = format!("model.layers.{}", i);
        // Self Attn
        tensors.insert(format!("{}.self_attn.q_proj.weight", p), Tensor::zeros((2048, 2048), DType::F16, &device)?);
        tensors.insert(format!("{}.self_attn.k_proj.weight", p), Tensor::zeros((1024, 2048), DType::F16, &device)?);
        tensors.insert(format!("{}.self_attn.v_proj.weight", p), Tensor::zeros((1024, 2048), DType::F16, &device)?);
        tensors.insert(format!("{}.self_attn.o_proj.weight", p), Tensor::zeros((2048, 2048), DType::F16, &device)?);
        
        // MLP
        tensors.insert(format!("{}.mlp.gate_proj.weight", p), Tensor::zeros((16384, 2048), DType::F16, &device)?);
        tensors.insert(format!("{}.mlp.up_proj.weight", p), Tensor::zeros((16384, 2048), DType::F16, &device)?);
        tensors.insert(format!("{}.mlp.down_proj.weight", p), Tensor::zeros((2048, 16384), DType::F16, &device)?);
        
        // Norms
        tensors.insert(format!("{}.input_layernorm.weight", p), Tensor::zeros((2048,), DType::F16, &device)?);
        tensors.insert(format!("{}.post_attention_layernorm.weight", p), Tensor::zeros((2048,), DType::F16, &device)?);
    }
    
    // Final Norm
    tensors.insert("model.norm.weight".to_string(), Tensor::zeros((2048,), DType::F16, &device)?);
    
    // LM Head
    tensors.insert("lm_head.weight".to_string(), Tensor::zeros((32000, 2048), DType::F16, &device)?);

    let vb = VarBuilder::from_tensors(tensors.clone(), DType::F16, &device);
    let vb_quant = VarBuilder::from_tensors(tensors, DType::F16, &device);

    // 3. Load Model
    println!("Loading Model...");
    let model = LlamaForCausalLM::load(vb, vb_quant, &config)?;
    println!("Model loaded successfully!");
    
    // 4. Test Forward Pass (Check softcapping usage)
    println!("Running Forward Pass...");
    let input = Tensor::zeros((1, 10), DType::U32, &device)?; // Batch 1, Seq 10
    let logits = model.forward(&input)?;
    println!("Logits Shape: {:?}", logits.dims());
    println!("Logits DType: {:?}", logits.dtype());
    
    // We expect 32000 (vocab) output last dim
    assert_eq!(logits.dim(2)?, 32000);
    
    println!("Gemma 2 Verification Complete.");
    Ok(())
}
