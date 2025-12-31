fn log_action(action: &str, payload: Option<String>) -> String {
    let payload_text = payload.clone().unwrap_or_else(|| "none".to_string());
    println!("ui_action: {} | payload: {}", action, payload_text);

    match payload {
        Some(value) if !value.trim().is_empty() => format!("Action: {} | Payload: {}", action, value),
        _ => format!("Action: {}", action),
    }
}

#[tauri::command]
pub fn voice_input_toggle(payload: Option<String>) -> String {
    log_action("voice_input_toggle", payload)
}

#[tauri::command]
pub fn manual_text_input(payload: Option<String>) -> String {
    log_action("manual_text_input", payload)
}

#[tauri::command]
pub fn transcript_drawer(payload: Option<String>) -> String {
    log_action("transcript_drawer", payload)
}

#[tauri::command]
pub fn memory_log_panel(payload: Option<String>) -> String {
    log_action("memory_log_panel", payload)
}

#[tauri::command]
pub fn context_snapshot_button(payload: Option<String>) -> String {
    log_action("context_snapshot_button", payload)
}

#[tauri::command]
pub fn library_tab(payload: Option<String>) -> String {
    log_action("library_tab", payload)
}

#[tauri::command]
pub fn web_search_button(payload: Option<String>) -> String {
    log_action("web_search_button", payload)
}

#[tauri::command]
pub fn reminder_button(payload: Option<String>) -> String {
    log_action("reminder_button", payload)
}

#[tauri::command]
pub fn calendar_view(payload: Option<String>) -> String {
    log_action("calendar_view", payload)
}

#[tauri::command]
pub fn command_console(payload: Option<String>) -> String {
    log_action("command_console", payload)
}

#[tauri::command]
pub fn style_panel(payload: Option<String>) -> String {
    log_action("style_panel", payload)
}

#[tauri::command]
pub fn settings_config(payload: Option<String>) -> String {
    log_action("settings_config", payload)
}

#[tauri::command]
pub fn privacy_control_panel(payload: Option<String>) -> String {
    log_action("privacy_control_panel", payload)
}

#[tauri::command]
pub fn inter_agent_comms_panel(payload: Option<String>) -> String {
    log_action("inter_agent_comms_panel", payload)
}

#[tauri::command]
pub fn fallback_mode_toggle(payload: Option<String>) -> String {
    log_action("fallback_mode_toggle", payload)
}

#[tauri::command]
pub fn save_context_now(payload: Option<String>) -> String {
    log_action("save_context_now", payload)
}

#[tauri::command]
pub fn silent_mode_button(payload: Option<String>) -> String {
    log_action("silent_mode_button", payload)
}

#[tauri::command]
pub fn restart_agent_session(payload: Option<String>) -> String {
    log_action("restart_agent_session", payload)
}

#[tauri::command]
pub fn load_custom_art(payload: Option<String>) -> String {
    log_action("load_custom_art", payload)
}
