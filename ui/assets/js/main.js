const API_BASE = 'http://localhost:8081';
let currentMode = 'chat';

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
            
            // System Memory (RAM)
            if (metrics.system) {
                const ramUsed = (metrics.system.memory_used_gb || 0).toFixed(1);
                const ramTotal = (metrics.system.memory_total_gb || 0).toFixed(1);
                document.getElementById('ramStatus').textContent = `${ramUsed} / ${ramTotal} GB`;
            }

            // GPU Memory (VRAM) - Assuming single GPU for now
            if (metrics.gpu && metrics.gpu.length > 0) {
                const gpu = metrics.gpu[0];
                const vramUsed = (gpu.memory_used_gb || 0).toFixed(1);
                const vramTotal = (gpu.memory_total_gb || 0).toFixed(1);
                document.getElementById('vramStatus').textContent = `${vramUsed} / ${vramTotal} GB`;
            }

            // Token Speeds (Placeholder logic - needs backend support for real-time t/s)
            // Ideally, the backend metrics should provide 'vorpal_tps' and 'goblin_tps'
            // For now, we'll display "Idle" or the last known speed if available
            const vorpalSpeed = metrics.vorpal_tps ? metrics.vorpal_tps.toFixed(1) : '--';
            const goblinSpeed = metrics.goblin_tps ? metrics.goblin_tps.toFixed(1) : '--';
            
            document.getElementById('vorpalSpeed').textContent = `${vorpalSpeed} t/s`;
            document.getElementById('goblinSpeed').textContent = `${goblinSpeed} t/s`;
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

function createMessage(content, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    msgDiv.appendChild(contentDiv);
    return msgDiv;
}

function createAgentMessage(response, data) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-agent';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = response;
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

        if (currentMode === 'chat') {
            chatContainer.appendChild(createMessage(data.response, 'agent'));
        } else if (currentMode === 'verify') {
            chatContainer.appendChild(createMessage(data.final_response, 'agent'));
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

userInput.focus();
