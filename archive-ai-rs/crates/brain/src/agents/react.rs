use async_trait::async_trait;
use anyhow::Result;
use crate::agents::{Agent, Tool};
use std::sync::Arc;
use tracing::{info, warn, error};
use serde_json::json;

pub struct ReActAgent {
    tools: Vec<Arc<dyn Tool>>,
    model: String,
    engine_url: String,
    client: reqwest::Client,
    max_steps: usize,
}

impl ReActAgent {
    pub fn new(model: String, engine_url: String) -> Self {
        Self {
            tools: Vec::new(),
            model,
            engine_url,
            client: reqwest::Client::new(),
            max_steps: 10,
        }
    }

    pub fn register_tool(&mut self, tool: Arc<dyn Tool>) {
        self.tools.push(tool);
    }

    fn build_prompt(&self, question: &str, history: &str) -> String {
        let mut p = String::new();
        p.push_str("You are a helpful AI assistant with access to these tools:\n");
        for t in &self.tools {
            p.push_str("- ");
            p.push_str(t.name());
            p.push_str(": ");
            p.push_str(t.description());
            p.push_str("\n");
        }
        p.push_str("\nUse this format:\nQuestion: the input question\nThought: what you are thinking\nAction: tool name\nAction Input: tool input\nObservation: tool result\n... (repeat loop)\nFinal Answer: final response\n\nQuestion: ");
        p.push_str(question);
        p.push_str("\n");
        p.push_str(history);
        p
    }
}

#[async_trait]
impl Agent for ReActAgent {
    async fn chat(&self, input: &str) -> Result<String> {
        info!("ReAct loop starting for: {}", input);
        let mut history = String::new();
        
        for step in 1..=self.max_steps {
            let prompt = self.build_prompt(input, &history);
            
            let mut url = self.engine_url.clone();
            url.push_str("/v1/chat/completions");

            let res = self.client.post(&url)
                .json(&json!({
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stop": ["Observation:"]
                }))
                .send()
                .await?;

            let body: serde_json::Value = res.json().await?;
            let content = body["choices"][0]["message"]["content"].as_str().unwrap_or("");
            
            history.push_str(content);
            info!("Step {}: {}", step, content);

            if content.contains("Final Answer:") {
                let parts: Vec<&str> = content.split("Final Answer:").collect();
                return Ok(parts.last().unwrap_or(&content).trim().to_string());
            }

            if let Some(action_line) = content.lines().find(|l| l.starts_with("Action:")) {
                let action_name = action_line.replace("Action:", "").trim().to_string();
                let input_line = content.lines().find(|l| l.starts_with("Action Input:")).unwrap_or("");
                let action_input = input_line.replace("Action Input:", "").trim().to_string();

                if let Some(tool) = self.tools.iter().find(|t| t.name() == action_name) {
                    info!("Executing tool: {}", action_name);
                    let observation = tool.execute(&action_input).await?;
                    history.push_str("\nObservation: ");
                    history.push_str(&observation);
                    history.push_str("\nThought:");
                } else {
                    let err_msg = "Tool not found.";
                    history.push_str("\nObservation: ");
                    history.push_str(err_msg);
                    history.push_str("\nThought:");
                }
            } else {
                warn!("No action found in response, retrying...");
                history.push_str("\nThought: I should use a tool or provide a final answer.");
            }
        }
        
        Ok("Max steps reached without answer.".to_string())
    }
}