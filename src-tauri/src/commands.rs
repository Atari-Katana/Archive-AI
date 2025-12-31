#[tauri::command]
pub fn ui_action(action: String, payload: Option<String>) -> String {
    let payload_text = payload.clone().unwrap_or_else(|| "none".to_string());
    println!("ui_action: {} | payload: {}", action, payload_text);

    match payload {
        Some(value) if !value.trim().is_empty() => format!("Action: {} | Payload: {}", action, value),
        _ => format!("Action: {}", action),
    }
}
