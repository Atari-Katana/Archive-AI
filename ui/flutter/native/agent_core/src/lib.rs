use std::ffi::CString;
use std::os::raw::c_char;
use std::sync::{Mutex, OnceLock};

static AGENT: OnceLock<Mutex<Agent>> = OnceLock::new();

#[derive(Debug, Clone, Copy, PartialEq)]
enum AgentMode {
    Normal,
    Fallback,
}

impl AgentMode {
    fn label(self) -> &'static str {
        match self {
            AgentMode::Normal => "NORMAL",
            AgentMode::Fallback => "FALLBACK",
        }
    }
}

#[derive(Debug, Clone, Copy)]
enum AgentAction {
    MicToggle,
    ManualInput,
    ToggleFallback,
    WebSearch,
    CalendarView,
    ContextView,
    OpenSettings,
    ToggleSilentMode,
}

impl AgentAction {
    fn from_u32(value: u32) -> Self {
        match value {
            0 => AgentAction::MicToggle,
            1 => AgentAction::ManualInput,
            2 => AgentAction::ToggleFallback,
            3 => AgentAction::WebSearch,
            4 => AgentAction::CalendarView,
            5 => AgentAction::ContextView,
            6 => AgentAction::OpenSettings,
            7 => AgentAction::ToggleSilentMode,
            _ => AgentAction::ManualInput,
        }
    }
}

#[derive(Debug)]
struct AgentSnapshot {
    mode: String,
    cpu_usage: f32,
    cpu_percent: u8,
    mic_enabled: bool,
    silent_mode: bool,
    transcript: Vec<String>,
}

#[derive(Debug)]
struct Agent {
    mode: AgentMode,
    cpu_usage: f32,
    mic_enabled: bool,
    silent_mode: bool,
    transcript: Vec<String>,
}

impl Agent {
    fn new() -> Self {
        Self {
            mode: AgentMode::Normal,
            cpu_usage: 0.38,
            mic_enabled: false,
            silent_mode: false,
            transcript: vec![
                "> Clara: Good morning, Mr. Jackson.".to_string(),
                "> You: What's the weather in Sommerfeld today?".to_string(),
                "> Clara: Foggy, but charming.".to_string(),
            ],
        }
    }

    fn handle_action(&mut self, action: AgentAction) {
        match action {
            AgentAction::MicToggle => {
                self.mic_enabled = !self.mic_enabled;
                self.push_line(format!(
                    "> System: Mic {}",
                    if self.mic_enabled { "enabled" } else { "disabled" }
                ));
            }
            AgentAction::ManualInput => {
                self.push_line("> System: Manual input requested.".to_string());
            }
            AgentAction::ToggleFallback => {
                self.mode = match self.mode {
                    AgentMode::Normal => AgentMode::Fallback,
                    AgentMode::Fallback => AgentMode::Normal,
                };
                self.push_line(format!(
                    "> Clara: Fallback mode {}.",
                    if self.mode == AgentMode::Fallback {
                        "enabled"
                    } else {
                        "disabled"
                    }
                ));
            }
            AgentAction::WebSearch => {
                self.push_line("> System: Web search triggered.".to_string());
            }
            AgentAction::CalendarView => {
                self.push_line("> System: Calendar view opened.".to_string());
            }
            AgentAction::ContextView => {
                self.push_line("> System: Context snapshot requested.".to_string());
            }
            AgentAction::OpenSettings => {
                self.push_line("> System: Settings opened.".to_string());
            }
            AgentAction::ToggleSilentMode => {
                self.silent_mode = !self.silent_mode;
                self.push_line(format!(
                    "> System: Silent mode {}",
                    if self.silent_mode { "enabled" } else { "disabled" }
                ));
            }
        }
    }

    fn snapshot(&self) -> AgentSnapshot {
        AgentSnapshot {
            mode: self.mode.label().to_string(),
            cpu_usage: self.cpu_usage,
            cpu_percent: (self.cpu_usage * 100.0).round() as u8,
            mic_enabled: self.mic_enabled,
            silent_mode: self.silent_mode,
            transcript: self.transcript.clone(),
        }
    }

    fn push_line(&mut self, line: String) {
        self.transcript.push(line);
    }
}

#[no_mangle]
pub extern "C" fn agent_snapshot() -> *mut c_char {
    let agent = AGENT
        .get_or_init(|| Mutex::new(Agent::new()))
        .lock()
        .expect("agent lock poisoned");
    snapshot_to_ptr(agent.snapshot())
}

#[no_mangle]
pub extern "C" fn agent_handle_action(action: u32) -> *mut c_char {
    let mut agent = AGENT
        .get_or_init(|| Mutex::new(Agent::new()))
        .lock()
        .expect("agent lock poisoned");
    agent.handle_action(AgentAction::from_u32(action));
    snapshot_to_ptr(agent.snapshot())
}

#[no_mangle]
pub extern "C" fn agent_free(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        drop(CString::from_raw(ptr));
    }
}

fn snapshot_to_ptr(snapshot: AgentSnapshot) -> *mut c_char {
    let json = snapshot_to_json(snapshot);
    CString::new(json).expect("snapshot json contained null byte").into_raw()
}

fn snapshot_to_json(snapshot: AgentSnapshot) -> String {
    let mut buffer = String::from("{");
    push_kv_string(&mut buffer, "mode", &snapshot.mode);
    buffer.push(',');
    push_kv_number(&mut buffer, "cpu_usage", snapshot.cpu_usage);
    buffer.push(',');
    push_kv_number(&mut buffer, "cpu_percent", snapshot.cpu_percent);
    buffer.push(',');
    push_kv_bool(&mut buffer, "mic_enabled", snapshot.mic_enabled);
    buffer.push(',');
    push_kv_bool(&mut buffer, "silent_mode", snapshot.silent_mode);
    buffer.push(',');
    buffer.push_str("\"transcript\":[");
    for (index, line) in snapshot.transcript.iter().enumerate() {
        if index > 0 {
            buffer.push(',');
        }
        push_string(&mut buffer, line);
    }
    buffer.push_str("]}");
    buffer
}

fn push_kv_string(buffer: &mut String, key: &str, value: &str) {
    push_string(buffer, key);
    buffer.push(':');
    push_string(buffer, value);
}

fn push_kv_number<T: std::fmt::Display>(buffer: &mut String, key: &str, value: T) {
    push_string(buffer, key);
    buffer.push(':');
    buffer.push_str(&value.to_string());
}

fn push_kv_bool(buffer: &mut String, key: &str, value: bool) {
    push_string(buffer, key);
    buffer.push(':');
    buffer.push_str(if value { "true" } else { "false" });
}

fn push_string(buffer: &mut String, value: &str) {
    buffer.push('"');
    for ch in value.chars() {
        match ch {
            '"' => buffer.push_str("\\\""),
            '\\' => buffer.push_str("\\\\"),
            '\n' => buffer.push_str("\\n"),
            '\r' => buffer.push_str("\\r"),
            '\t' => buffer.push_str("\\t"),
            other => buffer.push(other),
        }
    }
    buffer.push('"');
}
