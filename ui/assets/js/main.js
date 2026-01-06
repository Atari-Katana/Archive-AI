document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element Selectors ---
    const sessionList = document.getElementById('session-list');
    const chatLog = document.getElementById('chat-log');
    const messageInput = document.getElementById('B-01');
    const sendButton = document.getElementById('B-02');
    const stopButton = document.getElementById('B-03');
    const inspectorTabBar = document.querySelector('#right-inspect .tab-bar');
    const inspectorPanels = document.querySelectorAll('#inspector-content .tab-panel');

    // --- Event Listeners ---

    // 1. Right Inspector Tab Switching
    if (inspectorTabBar) {
        inspectorTabBar.addEventListener('click', (e) => {
            if (e.target.matches('.tab-button')) {
                const targetTab = e.target;
                const targetPanelId = targetTab.id.replace('R-', 'panel-');

                // Update tab buttons
                inspectorTabBar.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
                targetTab.classList.add('active');

                // Update tab panels
                // In a real app, you'd show the corresponding panel. For now, we'll just log it.
                console.log(`Switching to tab: ${targetTab.id}`);
                
                // This is a placeholder for showing the correct panel
                // inspectorPanels.forEach(panel => panel.classList.remove('active'));
                // document.getElementById(targetPanelId).classList.add('active');
            }
        });
    }

    // 2. Left Nav Session Selection
    if (sessionList) {
        sessionList.addEventListener('click', (e) => {
            if (e.target.closest('.session-item')) {
                sessionList.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
                e.target.closest('.session-item').classList.add('active');
            }
        });
    }

    // 3. Message Sending
    const sendMessage = () => {
        const text = messageInput.value.trim();
        if (!text) {
            return;
        }

        // Add user message to log
        addMessageToLog(text, 'user');
        messageInput.value = '';

        // --- Backend API call would go here ---

        // Simulate agent response
        toggleGeneratingState(true);
        setTimeout(() => {
            const simulatedResponse = `This is a simulated agent response to "${text}".`;
            addMessageToLog(simulatedResponse, 'agent');
            toggleGeneratingState(false);
        }, 1500);
    };

    if (sendButton) sendButton.addEventListener('click', sendMessage);
    if (messageInput) messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // 4. Stop Generation
    if (stopButton) {
        stopButton.addEventListener('click', () => {
            // In a real app, this would abort the fetch request to the backend
            console.log('Generation stopped.');
            toggleGeneratingState(false);
        });
    }


    // --- Helper Functions ---

    /**
     * Toggles the UI between generating and idle states.
     * @param {boolean} isGenerating - True if generation is starting, false if ending.
     */
    const toggleGeneratingState = (isGenerating) => {
        if (sendButton && stopButton) {
            sendButton.style.display = isGenerating ? 'none' : 'block';
            stopButton.style.display = isGenerating ? 'block' : 'none';
        }
        messageInput.disabled = isGenerating;
    };

    /**
     * Adds a message to the chat log.
     * @param {string} text - The message content.
     * @param {'user' | 'agent'} sender - The sender of the message.
     */
    const addMessageToLog = (text, sender) => {
        if (!chatLog) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const p = document.createElement('p');
        p.textContent = text;
        contentDiv.appendChild(p);

        // Add action buttons for agent messages
        if (sender === 'agent') {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            actionsDiv.innerHTML = `
                <button class="inline-button">Copy</button>
                <button class="inline-button">Regenerate</button>
            `;
            contentDiv.appendChild(actionsDiv);
        }
        
        messageDiv.appendChild(contentDiv);
        chatLog.appendChild(messageDiv);

        // Scroll to the bottom
        chatLog.scrollTop = chatLog.scrollHeight;
    };

});