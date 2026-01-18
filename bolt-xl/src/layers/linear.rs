use candle_core::{Tensor, Result};
use candle_nn::{Linear, Module, VarBuilder};
use crate::layers::quantization::AWQLinear;

pub enum LinearDispatch {
    Standard(Linear),
    Awq(AWQLinear),
}

impl Module for LinearDispatch {
    fn forward(&self, x: &Tensor) -> Result<Tensor> {
        match self {
            Self::Standard(l) => l.forward(x),
            Self::Awq(l) => l.forward(x),
        }
    }
}

pub struct ColumnParallelLinear {
    pub inner: LinearDispatch,
}

impl ColumnParallelLinear {
    pub fn new(linear: Linear) -> Self {
        Self { inner: LinearDispatch::Standard(linear) }
    }
    
    pub fn new_awq(linear: AWQLinear) -> Self {
        Self { inner: LinearDispatch::Awq(linear) }
    }
    
    pub fn load(vb: VarBuilder, vb_quant: VarBuilder, size: (usize, usize)) -> Result<Self> {
        // Try AWQ first (with dual VBs). AWQLinear expects (In, Out).
        // Linear load size is (Out, In).
        match AWQLinear::load(vb_quant.clone(), vb.clone(), (size.1, size.0)) {
            Ok(awq) => return Ok(Self::new_awq(awq)),
            Err(e) => {
                 // Only warn if it looked like an AWQ layer (has qweight)
                 if vb_quant.contains_tensor("qweight") {
                     println!("AWQ Load Failed for {:?}: {:?}", vb.prefix(), e);
                 }
            }
        }

        let weight = vb.get(size, "weight")?;
        let bias = if vb.contains_tensor("bias") {
             Some(vb.get(size.0, "bias")?)
        } else {
             None
        };
        Ok(Self::new(Linear::new(weight, bias)))
    }
}

impl Module for ColumnParallelLinear {
    fn forward(&self, xs: &Tensor) -> Result<Tensor> {
        self.inner.forward(xs)
    }
}

pub struct RowParallelLinear {
    pub inner: LinearDispatch,
}

impl RowParallelLinear {
    pub fn new(linear: Linear) -> Self {
        Self { inner: LinearDispatch::Standard(linear) }
    }

    pub fn new_awq(linear: AWQLinear) -> Self {
        Self { inner: LinearDispatch::Awq(linear) }
    }

    pub fn load(vb: VarBuilder, vb_quant: VarBuilder, size: (usize, usize)) -> Result<Self> {
         // Try AWQ first. AWQLinear expects (In, Out). Linear load size is (Out, In).
         // Try AWQ first. AWQLinear expects (In, Out). Linear load size is (Out, In).
        match AWQLinear::load(vb_quant.clone(), vb.clone(), (size.1, size.0)) {
            Ok(awq) => return Ok(Self::new_awq(awq)),
            Err(e) => {
                 if vb_quant.contains_tensor("qweight") {
                     println!("AWQ Load Failed for {:?}: {:?}", vb.prefix(), e);
                 }
            }
        }

        let weight = vb.get(size, "weight")?;
        let bias = if vb.contains_tensor("bias") {
             Some(vb.get(size.1, "bias")?)
        } else {
             None
        };
        Ok(Self::new(Linear::new(weight, bias)))
    }
}

impl Module for RowParallelLinear {
    fn forward(&self, xs: &Tensor) -> Result<Tensor> {
        self.inner.forward(xs)
    }
}

pub struct QKVParallelLinear {
    pub inner: LinearDispatch,
}

impl QKVParallelLinear {
    pub fn new(linear: Linear) -> Self {
        Self { inner: LinearDispatch::Standard(linear) }
    }
    
    // Helper to wrap dispatch
    pub fn new_dispatch(dispatch: LinearDispatch) -> Self {
        Self { inner: dispatch }
    }

    pub fn load(vb: VarBuilder, vb_quant: VarBuilder, size: (usize, usize)) -> Result<Self> {
         // Try AWS first (with dual VBs). AWQLinear expects (In, Out).
         // Linear load size is (Out, In).
         // Try AWS first (with dual VBs). AWQLinear expects (In, Out).
         // Linear load size is (Out, In).
        match AWQLinear::load(vb_quant.clone(), vb.clone(), (size.1, size.0)) {
            Ok(awq) => return Ok(Self::new_dispatch(LinearDispatch::Awq(awq))),
            Err(e) => {
                 if vb_quant.contains_tensor("qweight") {
                     println!("AWQ Load Failed for {:?}: {:?}", vb.prefix(), e);
                 }
            }
        }
        
        // Standard
        let weight = vb.get(size, "weight")?;
        let bias = if vb.contains_tensor("bias") {
             Some(vb.get(size.0, "bias")?)
        } else {
             None
        };
        Ok(Self::new(Linear::new(weight, bias)))
    }
}

impl Module for QKVParallelLinear {
    fn forward(&self, xs: &Tensor) -> Result<Tensor> {
        self.inner.forward(xs)
    }
}
