// --- Smart API Base Detection ---
const getApiBase = () => {
    const { protocol, hostname, port } = window.location;
    
    // The Brain (Orchestrator) is on Port 8080
    if (port === '8888') {
        return `http://${hostname}:8080`;
    }
    
    // For Cloudflare/Public domain, assume port 8080 is the primary Brain entry point
    return `${protocol}//${hostname}:8080`;
};

const API_BASE = getApiBase();
console.log("Archive Portal linked to Brain:", API_BASE);
let isThinking = false;
let mediaRecorder = null;
let audioChunks = [];

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const app = document.getElementById('app');
const clock = document.getElementById('clock');
const personaSelect = document.getElementById('personaSelect');
const personaPortrait = document.getElementById('personaPortrait');
const agentSelect = document.getElementById('agentSelect');
const configDrawer = document.getElementById('configDrawer');
const studioModal = document.getElementById('studioModal');

// Stats Elements
const statTPS = document.getElementById('statTPS');
const statVRAM = document.getElementById('statVRAM');
const statRAM = document.getElementById('statRAM');
const statDevice = document.getElementById('statDevice');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingStatus = document.getElementById('loadingStatus');
const loadingBar = document.getElementById('loadingBar');

// Clock Hands
const hourHand = document.getElementById('hourHand');
const minHand = document.getElementById('minHand');

// --- Clock Logic ---
function updateClock() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    
    const hDeg = (hours % 12) * 30 + minutes * 0.5;
    const mDeg = minutes * 6;

    hourHand.setAttribute('transform', `rotate(${hDeg}, 50, 50)`);
    minHand.setAttribute('transform', `rotate(${mDeg}, 50, 50)`);
    
    if (isThinking) {
        clock.classList.add('thinking');
    } else {
        clock.classList.remove('thinking');
    }
}

// --- Metrics Polling ---
async function fetchMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        if (!res.ok) return;
        const data = await res.json();
        
        if (data.system) {
            statTPS.textContent = (data.system.tokens_per_sec || 0).toFixed(1);
            statVRAM.textContent = `${Math.round(data.system.gpu_memory_percent || 0)}%`;
            statRAM.textContent = `${Math.round(data.system.memory_percent || 0)}%`;
            statDevice.textContent = data.system.device || "--";

            // Handle Loading Overlay
            const status = data.system.loading_status || "Ready";
            if (status !== "Ready") {
                loadingOverlay.style.display = "flex";
                loadingStatus.textContent = status.toUpperCase();
                
                // Heuristic for progress bar
                if (status.includes("Downloading")) loadingBar.style.width = "40%";
                else if (status.includes("Scanning")) loadingBar.style.width = "60%";
                else if (status.includes("Mapping")) loadingBar.style.width = "85%";
                else loadingBar.style.width = "20%";
            } else {
                loadingOverlay.style.display = "none";
            }
        }

        // Display Service Connectivity Status
        if (data.services) {
            data.services.forEach(s => {
                const el = document.getElementById(`status-${s.name}`);
                if (el) {
                    el.textContent = s.status.toUpperCase();
                    el.style.color = s.status === 'healthy' ? '#76c7b7' : '#ff4a4a';
                    el.style.fontWeight = 'bold';
                }
            });
        }
    } catch (e) { console.warn("Inference Core initializing..."); }
}

// --- Persona Management ---
async function loadPersonas() {
    try {
        const res = await fetch(`${API_BASE}/personas`);
        if (!res.ok) return;
        const personas = await res.json();
        
        personaSelect.innerHTML = '';
        personas.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            opt.dataset.portrait = p.avatar_path || '';
            opt.dataset.voice = p.voice_sample_path || '';
            personaSelect.appendChild(opt);
        });

        personaSelect.onchange = () => {
            const selected = personaSelect.options[personaSelect.selectedIndex];
            updatePortrait(selected.dataset.portrait);
            // Sync with backend
            fetch(`${API_BASE}/personas/activate/${selected.value}`, { method: 'POST' });
        };
        
        if(personas.length > 0) {
            personaSelect.selectedIndex = 0;
            updatePortrait(personas[0].avatar_path);
        }

    } catch (e) { console.error(e); }
}

function updatePortrait(url) {
    if (url) {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
        personaPortrait.innerHTML = `<img src="${fullUrl}" style="width:100%; height:100%; object-fit:cover;">`;
    } else {
        personaPortrait.innerHTML = `<span class="material-icons-round" style="margin: 10px;">account_circle</span>`;
    }
}

// --- Persona Studio ---
document.getElementById('openStudioBtn').onclick = () => {
    configDrawer.classList.remove('open');
    studioModal.style.display = 'block';
};

document.getElementById('closeStudioBtn').onclick = () => {
    studioModal.style.display = 'none';
};

// Avatar Upload
document.getElementById('avatarInput').onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    document.getElementById('avatarPreview').textContent = file.name;
};

// Voice Recording (6 seconds)
document.getElementById('recordVoiceBtn').onclick = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: 'audio/wav' });
            window.recordedVoiceBlob = blob;
            document.getElementById('voicePreview').textContent = "Voice clip captured (6s)";
            stream.getTracks().forEach(t => t.stop());
        };

        mediaRecorder.start();
        document.getElementById('recordVoiceBtn').textContent = "RECORDING...";
        document.getElementById('recordVoiceBtn').style.color = "red";

        setTimeout(() => {
            if (mediaRecorder.state === "recording") {
                mediaRecorder.stop();
                document.getElementById('recordVoiceBtn').textContent = "RECORD";
                document.getElementById('recordVoiceBtn').style.color = "";
            }
        }, 6000);

    } catch (e) { alert("Mic access denied"); }
};

document.getElementById('savePersonaBtn').onclick = async () => {
    const name = document.getElementById('studioName').value;
    const personality = document.getElementById('studioPersonality').value;
    const avatarFile = document.getElementById('avatarInput').files[0];
    const voiceBlob = window.recordedVoiceBlob;

    if (!name || !personality) {
        alert("Name and Personality are required.");
        return;
    }

    try {
        let avatarPath = "";
        let voicePath = "";

        // 1. Upload Avatar
        if (avatarFile) {
            const fd = new FormData();
            fd.append('file', avatarFile);
            fd.append('type', 'image');
            const res = await fetch(`${API_BASE}/personas/upload`, { method: 'POST', body: fd });
            const data = await res.json();
            avatarPath = data.path;
        }

        // 2. Upload Voice
        if (voiceBlob) {
            const fd = new FormData();
            fd.append('file', voiceBlob, 'voice.wav');
            fd.append('type', 'audio');
            const res = await fetch(`${API_BASE}/personas/upload`, { method: 'POST', body: fd });
            const data = await res.json();
            voicePath = data.path;
        }

        // 3. Create Persona
        const res = await fetch(`${API_BASE}/personas/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                personality,
                avatar_path: avatarPath,
                voice_sample_path: voicePath
            })
        });

        if (res.ok) {
            studioModal.style.display = 'none';
            loadPersonas();
            alert("Persona Initialized.");
        }
    } catch (e) { console.error(e); }
};

// --- Chat Logic ---
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    userInput.value = '';
    
    setThinking(true);

    try {
        const mode = agentSelect.value;
        let endpoint = "/chat";
        let payload = { message: text };

        if (mode === "basic") {
            endpoint = "/agent/";
            payload = { question: text };
        } else if (mode === "advanced") {
            endpoint = "/agent/advanced";
            payload = { question: text };
        } else if (mode === "recursive") {
            endpoint = "/agent/recursive";
            payload = { question: text, corpus: "general" }; // Default corpus
        } else if (mode === "coder") {
            endpoint = "/code_assist";
            payload = { task: text };
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        setThinking(false);

        if (data.response) {
            addMessage(data.response, 'agent', data.engine);
        }
        
    } catch (e) {
        setThinking(false);
        addMessage("CRITICAL ERROR: Archive connection severed.", 'agent');
    }
}

function setThinking(val) {
    isThinking = val;
    updateClock();
}

function addMessage(text, role, engine = "") {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    let html = "";
    if (typeof marked !== 'undefined') {
        html = marked.parse(text);
    } else {
        html = text;
    }

    if (role === 'agent' && engine) {
        html += `<div style="font-size: 0.7rem; opacity: 0.5; margin-top: 10px; font-family: monospace;">CORE: ${engine.toUpperCase()}</div>`;
    }

    msgDiv.innerHTML = html;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// --- UI Interaction ---
document.getElementById('openConfigBtn').onclick = () => configDrawer.classList.add('open');
document.getElementById('closeConfigBtn').onclick = () => configDrawer.classList.remove('open');
document.getElementById('clearBtn').onclick = () => { chatContainer.innerHTML = ''; configDrawer.classList.remove('open'); };

sendBtn.onclick = sendMessage;
userInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    setInterval(fetchMetrics, 3000); // Poll metrics
    loadPersonas();
    userInput.focus();
});