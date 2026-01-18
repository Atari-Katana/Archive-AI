use async_trait::async_trait;
use anyhow::Result;
use crate::agents::Tool;

pub mod code;

pub struct Calculator;

#[async_trait]
impl Tool for Calculator {
    fn name(&self) -> &str {
        "Calculator"
    }
    
    fn description(&self) -> &str {
        "Useful for math."
    }
    
    async fn execute(&self, input: &str) -> Result<String> {
        Ok(format!("Calculated: {}", input))
    }
}