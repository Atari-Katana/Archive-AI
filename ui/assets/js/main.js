const API_BASE = 'http://localhost:8081';
let currentMode = 'chat';
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// Configure Marked.js with Highlight.js
if (typeof marked !== 'undefined') {
    marked.setOptions({
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
        langPrefix: 'hljs language-',
        breaks: true,
        gfm: true
    });
}

// Fetch and display system status
async function updateSystemStatus() {
    try {
        // Fetch config for model name
        const configResp = await fetch(`${API_BASE}/config`);
        if (configResp.ok) {
            const data = await configResp.json();
            const modelName = data.config.vorpal_model || 'Unknown';
            const cleanName = modelName.split('/').pop();
            document.getElementById('modelStatus').textContent = cleanName;
        }

        // Fetch metrics for VRAM/RAM/Speed
        const metricsResp = await fetch(`${API_BASE}/metrics`);
        if (metricsResp.ok) {
            const metrics = await metricsResp.json();
            
            // System Memory (RAM) - Convert MB to GB
            if (metrics.system) {
                const ramUsed = (metrics.system.memory_used_mb / 1024).toFixed(1);
                const ramTotal = (metrics.system.memory_total_mb / 1024).toFixed(1);
                document.getElementById('ramStatus').textContent = `${ramUsed} / ${ramTotal} GB`;

                // GPU Memory (VRAM)
                // Backend might return null if running in container without GPU visibility
                if (metrics.system.gpu_memory_used_mb !== null && metrics.system.gpu_memory_total_mb !== null) {
                    const vramUsed = (metrics.system.gpu_memory_used_mb / 1024).toFixed(1);
                    const vramTotal = (metrics.system.gpu_memory_total_mb / 1024).toFixed(1);
                    document.getElementById('vramStatus').textContent = `${vramUsed} / ${vramTotal} GB`;
                } else {
                    document.getElementById('vramStatus').textContent = "-- / -- GB";
                }

                // Token Speed
                // Backend provides a global tokens_per_sec
                const tps = metrics.system.tokens_per_sec ? metrics.system.tokens_per_sec.toFixed(1) : '--';
                
                // For now, assign the same speed to Vorpal as it's the primary engine
                document.getElementById('vorpalSpeed').textContent = `${tps} t/s`;
                // Goblin speed isn't tracked separately in current metrics
                document.getElementById('goblinSpeed').textContent = `-- t/s`;
            }
        }

    } catch (error) {
        console.error('Failed to fetch status:', error);
        document.getElementById('modelStatus').textContent = 'Offline';
    }
}

// Update status every 5 seconds
setInterval(updateSystemStatus, 5000);

// Initial status check
updateSystemStatus();

// DOM elements
const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const toolUsageDiv = document.getElementById('toolUsage');
const modeBtns = document.querySelectorAll('.mode-btn');

// Mode selection
modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        currentMode = btn.dataset.mode;
        modeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const modeNames = {
            'chat': 'Chat',
            'verify': 'Verified',
            'agent': 'Basic Agent',
            'advanced': 'Advanced'
        };
        document.getElementById('currentMode').textContent = modeNames[currentMode];
    });
});

// Input handlers
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
sendBtn.addEventListener('click', sendMessage);

// Quick actions
document.getElementById('timeBtn').addEventListener('click', () => {
    userInput.value = 'What is the current date and time?';
    sendMessage();
});

document.getElementById('calcBtn').addEventListener('click', () => {
    userInput.value = 'Calculate 123 * 456';
    sendMessage();
});

document.getElementById('clearBtn').addEventListener('click', () => {
    chatContainer.textContent = '';
    const sysMsg = createMessage('Chat cleared. Start a new conversation!', 'system');
    chatContainer.appendChild(sysMsg);
    toolUsageDiv.textContent = '';
    const chip = document.createElement('span');
    chip.className = 'tool-chip';
    chip.textContent = 'No tools used';
    toolUsageDiv.appendChild(chip);
});

function createMessage(content, type, engine = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${type}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Render Markdown if available, otherwise use plain text
    if (typeof marked !== 'undefined') {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    msgDiv.appendChild(contentDiv);

    // Add speaker button and engine badge for agent messages
    if (type === 'agent') {
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'message-controls';
        
        // Engine Badge
        if (engine) {
            const badge = document.createElement('span');
            badge.className = 'engine-badge';
            // Clean up engine name (e.g., "bifrost:vorpal/..." -> "vorpal")
            let engineName = engine;
            if (engineName.includes(':')) {
                engineName = engineName.split(':')[1];
            }
            if (engineName.includes('/')) {
                engineName = engineName.split('/')[0];
            }
            badge.textContent = `⚙️ ${engineName}`;
            badge.title = `Generated by ${engine}`;
            controlsDiv.appendChild(badge);
        }

        // Speaker Button
        const speakerBtn = document.createElement('button');
        speakerBtn.className = 'speaker-btn';
        speakerBtn.textContent = '🔊';
        speakerBtn.title = 'Play as audio';
        speakerBtn.onclick = () => speakText(content, msgDiv);
        controlsDiv.appendChild(speakerBtn);
        
        msgDiv.appendChild(controlsDiv);
    }

    return msgDiv;
}

function createAgentMessage(response, data) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-agent';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Render Markdown if available
    if (typeof marked !== 'undefined') {
        contentDiv.innerHTML = marked.parse(response);
    } else {
        contentDiv.textContent = response;
    }
    
    msgDiv.appendChild(contentDiv);

    if (data.steps && data.steps.length > 0) {
        const stepsDiv = document.createElement('div');
        stepsDiv.className = 'reasoning-steps';
        
        const title = document.createElement('strong');
        title.textContent = 'Reasoning Process:';
        stepsDiv.appendChild(title);

        const toolsUsed = new Set();

        data.steps.forEach(step => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step';

            const header = document.createElement('div');
            header.className = 'step-header';
            header.textContent = `Step ${step.step_number}`;
            stepDiv.appendChild(header);

            const thought = document.createElement('div');
            thought.className = 'step-detail';
            const thoughtLabel = document.createElement('span');
            thoughtLabel.className = 'step-label';
            thoughtLabel.textContent = 'Thought: ';
            thought.appendChild(thoughtLabel);
            thought.appendChild(document.createTextNode(step.thought));
            stepDiv.appendChild(thought);

            if (step.action && step.action !== 'Final Answer') {
                const action = document.createElement('div');
                action.className = 'step-detail';
                const actionLabel = document.createElement('span');
                actionLabel.className = 'step-label';
                actionLabel.textContent = 'Action: ';
                action.appendChild(actionLabel);
                action.appendChild(document.createTextNode(step.action));
                
                const badge = document.createElement('span');
                badge.className = 'tool-badge';
                badge.textContent = step.action;
                action.appendChild(badge);
                
                stepDiv.appendChild(action);
                toolsUsed.add(step.action);
            }

            if (step.action_input) {
                const input = document.createElement('div');
                input.className = 'step-detail';
                const inputLabel = document.createElement('span');
                inputLabel.className = 'step-label';
                inputLabel.textContent = 'Input: ';
                input.appendChild(inputLabel);
                input.appendChild(document.createTextNode(step.action_input));
                stepDiv.appendChild(input);
            }

            if (step.observation) {
                const obs = document.createElement('div');
                obs.className = 'step-detail';
                const obsLabel = document.createElement('span');
                obsLabel.className = 'step-label';
                obsLabel.textContent = 'Result: ';
                obs.appendChild(obsLabel);
                obs.appendChild(document.createTextNode(step.observation));
                stepDiv.appendChild(obs);
            }

            stepsDiv.appendChild(stepDiv);
        });

        msgDiv.appendChild(stepsDiv);

        if (toolsUsed.size > 0) {
            updateToolUsage(Array.from(toolsUsed));
        }
    }

    // Add controls
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'message-controls';

    // Speaker Button
    const speakerBtn = document.createElement('button');
    speakerBtn.className = 'speaker-btn';
    speakerBtn.textContent = '🔊';
    speakerBtn.title = 'Play as audio';
    speakerBtn.onclick = () => speakText(response, msgDiv);
    controlsDiv.appendChild(speakerBtn);

    msgDiv.appendChild(controlsDiv);

    return msgDiv;
}

function updateToolUsage(tools) {
    toolUsageDiv.textContent = '';
    tools.forEach(tool => {
        const chip = document.createElement('span');
        chip.className = 'tool-chip';
        chip.textContent = tool;
        toolUsageDiv.appendChild(chip);
    });
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    chatContainer.appendChild(createMessage(message, 'user'));
    userInput.value = '';

    sendBtn.disabled = true;
    sendBtn.textContent = 'Thinking...';

    // Update Engine status
    const lastEngineEl = document.getElementById('lastEngine');
    if (lastEngineEl) {
        lastEngineEl.textContent = 'Thinking...';
    }

    try {
        let endpoint, payload;
        switch(currentMode) {
            case 'chat':
                endpoint = '/chat';
                payload = { message };
                break;
            case 'verify':
                endpoint = '/verify';
                payload = { message };
                break;
            case 'agent':
                endpoint = '/agent';
                payload = { question: message, max_steps: 10 };
                break;
            case 'advanced':
                endpoint = '/agent/advanced';
                payload = { question: message, max_steps: 10 };
                break;
        }

        const response = await fetch(API_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        // Update Last Engine status
        if (data.engine) {
            let engineName = data.engine;
            // Clean up name (e.g., "bifrost:vorpal/..." -> "vorpal")
            if (engineName.includes(':')) {
                engineName = engineName.split(':')[1];
            }
            if (engineName.includes('/')) {
                engineName = engineName.split('/')[0];
            }
            const lastEngineEl = document.getElementById('lastEngine');
            if (lastEngineEl) {
                lastEngineEl.textContent = engineName;
            }
        }

        if (currentMode === 'chat') {
            chatContainer.appendChild(createMessage(data.response, 'agent', data.engine));
        } else if (currentMode === 'verify') {
            chatContainer.appendChild(createMessage(data.final_response, 'agent', data.engine));
        } else {
            chatContainer.appendChild(createAgentMessage(data.answer || 'Task completed!', data));
        }

    } catch (error) {
        chatContainer.appendChild(createMessage('Error: ' + error.message, 'system'));
    }

    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
    chatContainer.scrollTop = chatContainer.scrollHeight;
    userInput.focus();
}

// Voice recording functionality
const voiceBtn = document.getElementById('voiceBtn');

voiceBtn.addEventListener('click', async () => {
    if (!isRecording) {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                await transcribeAudio(audioBlob);

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            voiceBtn.textContent = '⏹️';
            voiceBtn.title = 'Stop recording';
            voiceBtn.style.background = '#ef4444';
        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('Could not access microphone. Please grant permission and try again.');
        }
    } else {
        // Stop recording
        mediaRecorder.stop();
        isRecording = false;
        voiceBtn.textContent = '🎤';
        voiceBtn.title = 'Record voice input';
        voiceBtn.style.background = '';
    }
});

async function transcribeAudio(audioBlob) {
    sendBtn.disabled = true;
    sendBtn.textContent = 'Transcribing...';

    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        const response = await fetch(`${API_BASE}/voice/transcribe`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            userInput.value = data.text;
            // Automatically send the transcribed text
            sendMessage();
        } else {
            const error = await response.json();
            chatContainer.appendChild(createMessage(`Voice transcription failed: ${error.detail}`, 'system'));
        }
    } catch (error) {
        console.error('Transcription error:', error);
        chatContainer.appendChild(createMessage(`Voice transcription error: ${error.message}`, 'system'));
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
    }
}

async function speakText(text, messageElement) {
    try {
        // Add a loading indicator
        const speakerBtn = messageElement.querySelector('.speaker-btn');
        if (speakerBtn) {
            speakerBtn.textContent = '⏳';
            speakerBtn.disabled = true;
        }

        const response = await fetch(`${API_BASE}/voice/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (response.ok) {
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                if (speakerBtn) {
                    speakerBtn.textContent = '🔊';
                    speakerBtn.disabled = false;
                }
            };

            audio.play();
        } else {
            const error = await response.json();
            console.error('TTS error:', error);
            alert(`Voice synthesis failed: ${error.detail}`);
            if (speakerBtn) {
                speakerBtn.textContent = '🔊';
                speakerBtn.disabled = false;
            }
        }
    } catch (error) {
        console.error('TTS error:', error);
        alert(`Voice synthesis error: ${error.message}`);
    }
}

userInput.focus();

/* ==========================================
   Persona Management Logic
   ========================================== */

const personaDropdownBtn = document.getElementById('personaDropdownBtn');
const personaDropdownList = document.getElementById('personaDropdownList');
const openStudioBtn = document.getElementById('openStudioBtn');
const personaModal = document.getElementById('personaModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const personaForm = document.getElementById('personaForm');
const personaListItems = document.getElementById('personaListItems');
const currentPersonaName = document.getElementById('currentPersonaName');

// Dropdown Toggle
if (personaDropdownBtn) {
    personaDropdownBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        document.querySelector('.persona-dropdown').classList.toggle('active');
    });
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (document.querySelector('.persona-dropdown') && !e.target.closest('.persona-dropdown')) {
        document.querySelector('.persona-dropdown').classList.remove('active');
    }
});

// Modal Controls
if (openStudioBtn) {
    openStudioBtn.addEventListener('click', () => {
        openPersonaModal();
        document.querySelector('.persona-dropdown').classList.remove('active');
    });
}

if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
        personaModal.style.display = 'none';
    });
}

window.addEventListener('click', (e) => {
    if (e.target === personaModal) {
        personaModal.style.display = 'none';
    }
});

// Load Personas on startup
async function loadPersonas() {
    try {
        const [listResp, activeResp] = await Promise.all([
            fetch(`${API_BASE}/personas`),
            fetch(`${API_BASE}/personas/active`)
        ]);
        
        const personas = await listResp.json();
        const activeData = await activeResp.json();
        const activeId = activeData.active_persona_id;
        
        renderPersonaList(personas, activeId);
        
        if (activeData.persona) {
            currentPersonaName.textContent = activeData.persona.name;
        } else {
            currentPersonaName.textContent = "Select Persona";
        }
        
    } catch (error) {
        console.error("Failed to load personas:", error);
    }
}

function renderPersonaList(personas, activeId) {
    if (!personaListItems) return;
    personaListItems.innerHTML = '';
    
    if (personas.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'dropdown-item';
        empty.style.color = '#999';
        empty.style.fontStyle = 'italic';
        empty.textContent = 'No personas created';
        personaListItems.appendChild(empty);
        return;
    }
    
    personas.forEach(persona => {
        const item = document.createElement('div');
        item.className = 'persona-item';
        
        const isActive = persona.id === activeId;
        
        // Use onclick attributes for simplicity in this context
        item.innerHTML = `
            <div class="persona-name-container" onclick="activatePersona('${persona.id}')">
                <span class="persona-name">${persona.name}</span>
                ${isActive ? '<span class="active-check">✓</span>' : ''}
            </div>
            <div class="persona-controls">
                <span class="control-icon" title="Edit" onclick="editPersona('${persona.id}')">✏️</span>
                <span class="control-icon" title="Delete" onclick="deletePersona('${persona.id}', '${persona.name}')">🗑️</span>
            </div>
        `;
        
        personaListItems.appendChild(item);
    });
}

window.activatePersona = async (id) => {
    try {
        await fetch(`${API_BASE}/personas/activate/${id}`, { method: 'POST' });
        loadPersonas(); // Refresh UI
        document.querySelector('.persona-dropdown').classList.remove('active');
        
        // Add system message
        const resp = await fetch(`${API_BASE}/personas/active`);
        const data = await resp.json();
        if (data.persona) {
            chatContainer.appendChild(createMessage(`**System**: Activated persona **${data.persona.name}**`, 'system'));
        }
    } catch (error) {
        console.error("Failed to activate persona:", error);
    }
}

function openPersonaModal(persona = null) {
    const title = document.getElementById('modalTitle');
    const btn = document.getElementById('savePersonaBtn');
    
    // Clear form
    if (personaForm) personaForm.reset();
    document.getElementById('personaId').value = '';
    document.getElementById('avatarPreview').innerHTML = '';
    document.getElementById('voicePreview').innerHTML = '';
    
    if (persona) {
        // Edit Mode
        title.textContent = 'Edit Persona';
        btn.textContent = 'Update Persona';
        
        document.getElementById('personaId').value = persona.id;
        document.getElementById('personaName').value = persona.name;
        document.getElementById('personaPersonality').value = persona.personality;
        document.getElementById('personaHistory').value = persona.history || '';
        
        if (persona.avatar_path) {
            document.getElementById('avatarPreview').innerHTML = 
                `<img src="${API_BASE}/ui/${persona.avatar_path}" alt="Avatar">`;
        }
    } else {
        // Create Mode
        title.textContent = 'Persona Studio';
        btn.textContent = 'Create Persona';
    }
    
    personaModal.style.display = 'block';
}

// Edit Trigger
window.editPersona = async (id) => {
    const listResp = await fetch(`${API_BASE}/personas`);
    const personas = await listResp.json();
    const persona = personas.find(p => p.id === id);
    if (persona) {
        openPersonaModal(persona);
        document.querySelector('.persona-dropdown').classList.remove('active');
    }
};

// Delete Trigger
window.deletePersona = async (id, name) => {
    if (confirm(`Are you sure you want to delete ${name}?`)) {
        try {
            await fetch(`${API_BASE}/personas/${id}`, { method: 'DELETE' });
            loadPersonas();
        } catch (error) {
            alert("Failed to delete persona");
        }
    }
};

// Form Submission
if (personaForm) {
    personaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById('savePersonaBtn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Saving...';
        
        const id = document.getElementById('personaId').value;
        const name = document.getElementById('personaName').value;
        const personality = document.getElementById('personaPersonality').value;
        const history = document.getElementById('personaHistory').value;
        const avatarFile = document.getElementById('personaAvatar').files[0];
        const voiceFile = document.getElementById('personaVoice').files[0];
        
        // Upload assets first if present
        let avatarPath = null;
        let voicePath = null;
        
        try {
            if (avatarFile) {
                const formData = new FormData();
                formData.append('file', avatarFile);
                formData.append('type', 'image');
                const resp = await fetch(`${API_BASE}/personas/upload`, { method: 'POST', body: formData });
                if (resp.ok) {
                    avatarPath = (await resp.json()).path;
                }
            }
            
            if (voiceFile) {
                const formData = new FormData();
                formData.append('file', voiceFile);
                formData.append('type', 'audio');
                const resp = await fetch(`${API_BASE}/personas/upload`, { method: 'POST', body: formData });
                if (resp.ok) {
                    voicePath = (await resp.json()).path;
                }
            }
            
            const payload = {
                name,
                personality,
                history
            };
            
            if (avatarPath) payload.avatar_path = avatarPath;
            if (voicePath) payload.voice_sample_path = voicePath;
            
            if (id) {
                // Update
                await fetch(`${API_BASE}/personas/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Create
                await fetch(`${API_BASE}/personas`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }
            
            personaModal.style.display = 'none';
            loadPersonas();
            
        } catch (error) {
            console.error("Error saving persona:", error);
            alert("Error saving persona: " + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    });
}

// Initialize
loadPersonas();