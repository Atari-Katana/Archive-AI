use async_trait::async_trait;
use anyhow::Result;
use crate::agents::Tool;
use shared::AppConfig;
use serde_json::json;

pub struct CodeExecution {
    pub config: AppConfig,
    pub client: reqwest::Client,
}

impl CodeExecution {
    pub fn new(config: AppConfig) -> Self {
        Self {
            config,
            client: reqwest::Client::new(),
        }
    }
}

#[async_trait]
impl Tool for CodeExecution {
    fn name(&self) -> &str {
        "execute_code"
    }
    
    fn description(&self) -> &str {
        "Execute Python code in a safe sandbox. Use for calculations or data processing."
    }
    
    async fn execute(&self, input: &str) -> Result<String> {
        let url = format!("{}/execute", self.config.sandbox_url);
        let payload = json!({
            "code": input,
            "timeout": 30
        });

        let res = self.client.post(&url)
            .json(&payload)
            .send()
            .await?;

        if !res.status().is_success() {
            return Ok(format!("Error calling sandbox: {}", res.status()));
        }

        let body: serde_json::Value = res.json().await?;
        
        if body["status"] == "success" {
            Ok(body["result"].as_str().unwrap_or("Success (no output)").to_string())
        } else {
            Ok(format!("Execution failed: {}", body["error"].as_str().unwrap_or("Unknown error")))
        }
    }
}
