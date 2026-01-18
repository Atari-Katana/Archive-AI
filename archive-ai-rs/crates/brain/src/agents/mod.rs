use async_trait::async_trait;
use anyhow::Result;

pub mod react;
pub mod tools;

#[async_trait]
pub trait Agent {
    async fn chat(&self, input: &str) -> Result<String>;
}

#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    async fn execute(&self, input: &str) -> Result<String>;
}
