#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::voice_input_toggle,
            commands::manual_text_input,
            commands::transcript_drawer,
            commands::memory_log_panel,
            commands::context_snapshot_button,
            commands::library_tab,
            commands::web_search_button,
            commands::reminder_button,
            commands::calendar_view,
            commands::command_console,
            commands::style_panel,
            commands::settings_config,
            commands::privacy_control_panel,
            commands::inter_agent_comms_panel,
            commands::fallback_mode_toggle,
            commands::save_context_now,
            commands::silent_mode_button,
            commands::restart_agent_session,
            commands::load_custom_art
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
