// J.A.R.V.I.S. Frontend Master Controller
let ws = null;
let currentRMS = 0;
let targetRMS = 0;
let currentState = 'STANDBY';

// DOM Elements
const connectionStatus = document.getElementById('connectionStatus');
const stateBanner = document.getElementById('assistantStateBanner');
const stateLabel = document.getElementById('stateLabel');
const hudClock = document.getElementById('hudClock');
const hudDate = document.getElementById('hudDate');

// Telemetry DOM
const cpuVal = document.getElementById('cpuVal');
const cpuBar = document.getElementById('cpuBar');
const cpuCores = document.getElementById('cpuCores');
const ramVal = document.getElementById('ramVal');
const ramBar = document.getElementById('ramBar');
const ramDetail = document.getElementById('ramDetail');
const batteryVal = document.getElementById('batteryVal');
const batteryBar = document.getElementById('batteryBar');
const batteryStatus = document.getElementById('batteryStatus');
const uptimeVal = document.getElementById('uptimeVal');
const diskVal = document.getElementById('diskVal');

// Console DOM
const transcriptFeed = document.getElementById('transcriptFeed');
const clearLogBtn = document.getElementById('clearLogBtn');
const screenshotCard = document.getElementById('screenshotCard');
const screenshotImg = document.getElementById('screenshotImg');
const screenshotLink = document.getElementById('screenshotLink');
const closePreviewBtn = document.getElementById('closePreviewBtn');

// Interaction DOM
const commandForm = document.getElementById('commandForm');
const commandInput = document.getElementById('commandInput');
const reactorTrigger = document.getElementById('reactorTrigger');
const micBtn = document.getElementById('micBtn');
const diagBtn = document.getElementById('diagBtn');
const snapBtn = document.getElementById('snapBtn');
const muteBtn = document.getElementById('muteBtn');
const notesBtn = document.getElementById('notesBtn');
const lockBtn = document.getElementById('lockBtn');

// Canvas Audio Visualizer
const canvas = document.getElementById('visualizerCanvas');
const ctx = canvas.getContext('2d');

// Clock Update
function updateClock() {
    const now = new Date();
    hudClock.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    hudDate.textContent = now.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase();
}
setInterval(updateClock, 1000);
updateClock();

// WebSocket Setup
// Connection & Demo Mode State
let isDemoMode = false;
let connectionAttempts = 0;
let demoTelemetryInterval = null;

// WebSocket Setup
function connectWebSocket() {
    const isHostedOnGitHub = window.location.hostname.includes('github.io');
    
    // If hosted on GitHub Pages or file protocol, launch showcase mode directly
    if (isHostedOnGitHub || window.location.protocol === 'file:') {
        activateShowcaseMode();
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);
    } catch (e) {
        handleConnectionFailure();
        return;
    }

    ws.onopen = () => {
        isDemoMode = false;
        connectionAttempts = 0;
        if (demoTelemetryInterval) clearInterval(demoTelemetryInterval);
        connectionStatus.innerHTML = `
            <span class="status-dot"></span>
            <span class="status-text">SYSTEM ONLINE</span>
        `;
        connectionStatus.style.borderColor = 'rgba(0, 255, 170, 0.4)';
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        } catch (err) {
            console.error('[WS Parse Error]', err);
        }
    };

    ws.onclose = () => {
        handleConnectionFailure();
    };

    ws.onerror = (err) => {
        console.error('[WS Error]', err);
        ws.close();
    };
}

function handleConnectionFailure() {
    connectionAttempts++;
    if (connectionAttempts >= 2 && !isDemoMode) {
        activateShowcaseMode();
    } else if (!isDemoMode) {
        connectionStatus.innerHTML = `
            <span class="status-dot" style="background:#ff3366; box-shadow:0 0 8px #ff3366;"></span>
            <span class="status-text" style="color:#ff3366;">CONNECTING...</span>
        `;
        connectionStatus.style.borderColor = 'rgba(255, 51, 102, 0.4)';
    }
    setTimeout(connectWebSocket, 3000);
}

// Interactive Showcase / Demo Mode for GitHub Pages
function activateShowcaseMode() {
    isDemoMode = true;
    connectionStatus.innerHTML = `
        <span class="status-dot" style="background:#00f0ff; box-shadow:0 0 10px #00f0ff;"></span>
        <span class="status-text" style="color:#00f0ff;">SHOWCASE DEMO // ONLINE</span>
    `;
    connectionStatus.style.borderColor = 'rgba(0, 240, 255, 0.5)';

    // Initial message in transcript feed
    if (transcriptFeed.children.length === 0) {
        appendMessage('system', 'Mark VII Arc-Reactor HUD active in Showcase Mode. Systems nominal. Try clicking quick actions or typing a command!');
    }

    // Start simulated live telemetry
    if (!demoTelemetryInterval) {
        let simUptime = 3480;
        demoTelemetryInterval = setInterval(() => {
            simUptime += 2;
            const hours = Math.floor(simUptime / 3600);
            const minutes = Math.floor((simUptime % 3600) / 60);
            const cpu = Math.floor(14 + Math.random() * 18);
            const ram = (7.2 + Math.random() * 0.4).toFixed(1);
            const battery = 96;

            updateTelemetry({
                cpu_percent: cpu,
                cpu_cores: 8,
                ram_percent: Math.round((ram / 16.0) * 100),
                ram_used_gb: parseFloat(ram),
                ram_total_gb: 16.0,
                disk_percent: 42,
                battery_percent: battery,
                battery_plugged: true,
                uptime: `${hours}h ${minutes}m`
            });
        }, 2000);
    }
}

// Handle Server Messages
function handleServerMessage(msg) {
    switch (msg.type) {
        case 'init':
            if (msg.telemetry) updateTelemetry(msg.telemetry);
            if (msg.status) updateState(msg.status);
            break;

        case 'status_change':
            updateState(msg.status);
            break;

        case 'wake_detected':
            updateState('LISTENING');
            break;

        case 'speech_start':
            updateState('SPEAKING');
            break;

        case 'speech_stop':
            updateState('STANDBY');
            targetRMS = 0;
            break;

        case 'audio_amplitude':
            targetRMS = Math.min(1.0, msg.rms * 3.5);
            break;

        case 'mic_level':
            if (currentState === 'LISTENING') {
                targetRMS = Math.min(1.0, msg.rms / 600.0);
            }
            break;

        case 'telemetry_update':
            updateTelemetry(msg.telemetry);
            break;

        case 'user_message':
            appendMessage('user', msg.text);
            break;

        case 'assistant_response':
            appendMessage('assistant', msg.response, msg.action, msg.data);
            if (msg.action === 'screenshot' && msg.data && msg.data.filepath) {
                showScreenshotPreview(msg.data.filepath);
            }
            break;
    }
}

// Update State Banner & Reactor Styles
function updateState(state) {
    currentState = state;
    stateBanner.className = 'status-banner ' + state.toLowerCase();

    switch (state) {
        case 'LISTENING':
            stateLabel.textContent = 'LISTENING... // CAPTURING VOICE COMMAND';
            break;
        case 'PROCESSING':
            stateLabel.textContent = 'PROCESSING... // COMPUTING INTENT';
            break;
        case 'SPEAKING':
            stateLabel.textContent = 'SPEAKING... // VOCAL TRANSMISSION ACTIVE';
            break;
        default:
            stateLabel.textContent = 'STANDBY // LISTENING FOR "MANI"';
            break;
    }
}

// Update Telemetry Display
function updateTelemetry(data) {
    if (!data) return;

    // CPU
    cpuVal.textContent = `${data.cpu_percent}%`;
    cpuBar.style.width = `${Math.min(100, data.cpu_percent)}%`;
    if (data.cpu_cores) cpuCores.textContent = `${data.cpu_cores} LOGICAL THREADS`;

    // RAM
    ramVal.textContent = `${data.ram_percent}%`;
    ramBar.style.width = `${Math.min(100, data.ram_percent)}%`;
    ramDetail.textContent = `${data.ram_used_gb} GB / ${data.ram_total_gb} GB USED`;

    // Battery
    if (data.battery_percent !== null && data.battery_percent !== undefined) {
        batteryVal.textContent = `${data.battery_percent}%`;
        batteryBar.style.width = `${data.battery_percent}%`;
        const chargingStr = data.power_plugged ? '⚡ CHARGING (AC POWER)' : 'BATTERY DISCHARGING';
        batteryStatus.textContent = chargingStr;
    } else {
        batteryVal.textContent = 'N/A';
        batteryBar.style.width = '100%';
        batteryStatus.textContent = 'DESKTOP DIRECT POWER';
    }

    // Uptime & Disk
    if (data.uptime) uptimeVal.textContent = data.uptime;
    if (data.disk_free_gb) diskVal.textContent = `${data.disk_free_gb} GB FREE`;
}

// Append Message to Transcript Feed
function appendMessage(sender, text, action = null, data = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;

    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    const senderName = sender === 'user' ? 'COMMANDER' : 'M.A.N.I.';

    let actionBadge = '';
    if (action && action !== 'conversation' && action !== 'standby') {
        actionBadge = `<span class="panel-tag" style="margin-left: 8px;">${action.toUpperCase()}</span>`;
    }

    msgDiv.innerHTML = `
        <div class="msg-header">
            <div>
                <span class="msg-sender">${senderName}</span>
                ${actionBadge}
            </div>
            <span class="msg-time">${timeStr}</span>
        </div>
        <div class="msg-body">${escapeHTML(text)}</div>
    `;

    transcriptFeed.appendChild(msgDiv);
    transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

// Screenshot preview handler
function showScreenshotPreview(filepath) {
    const filename = filepath.split('\\').pop().split('/').pop();
    const url = `/screenshots/${filename}`;
    screenshotImg.src = url;
    screenshotLink.href = url;
    screenshotCard.style.display = 'block';
    transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
}

closePreviewBtn.addEventListener('click', () => {
    screenshotCard.style.display = 'none';
});

clearLogBtn.addEventListener('click', () => {
    transcriptFeed.innerHTML = '';
});

// User Input Submission
commandForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = commandInput.value.trim();
    if (!query) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'user_input', text: query }));
    } else if (isDemoMode) {
        handleDemoUserInput(query);
    }
    commandInput.value = '';
});

// Quick Action Triggers
function sendQuickAction(action) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'quick_action', action }));
    } else if (isDemoMode) {
        handleDemoAction(action);
    }
}

// Interactive Demo Responses & Speech Synthesis
function handleDemoUserInput(text) {
    appendMessage('user', text);
    updateState('THINKING');

    setTimeout(() => {
        const lower = text.toLowerCase();
        let reply = "At your service, sir. All systems are functioning at peak efficiency.";

        if (lower.includes('hello') || lower.includes('hi') || lower.includes('hey')) {
            reply = "Greetings, sir. Mani Mark VII online and standing by.";
        } else if (lower.includes('who are you') || lower.includes('what are you')) {
            reply = "I am M.A.N.I., an autonomous personal AI assistant inspired by Iron Man's J.A.R.V.I.S. I automate Windows workstations, manage applications, and assist with complex tasks.";
        } else if (lower.includes('time') || lower.includes('date')) {
            const now = new Date();
            reply = `The current time is ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} on ${now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })}.`;
        } else if (lower.includes('status') || lower.includes('diagnostics') || lower.includes('system')) {
            reply = "Diagnostics complete. CPU cores operating at nominal thermal index, memory consumption within safe thresholds, power reserves 96%. All operational.";
        } else if (lower.includes('joke')) {
            reply = "Why did the AI go to school? Because it wanted to improve its neural networks, sir.";
        } else if (lower.includes('open') || lower.includes('launch')) {
            reply = `Direct app execution is active when running on your local Windows PC. Simulating launch sequence for: ${text}.`;
        } else if (lower.includes('thank')) {
            reply = "Always a pleasure to be of service, sir.";
        } else {
            reply = `Command acknowledged: "${text}". Running in HUD Showcase mode. When connected to your local Windows backend, I execute this directly on your workstation.`;
        }

        appendMessage('assistant', reply);
        speakDemoResponse(reply);
    }, 450);
}

function handleDemoAction(action) {
    switch (action) {
        case 'telemetry':
            handleDemoUserInput('system status');
            break;
        case 'screenshot':
            appendMessage('system', 'Simulating display capture buffer...');
            setTimeout(() => {
                appendMessage('assistant', 'Display snapshot recorded to buffer. In local Windows mode, screenshots are saved to data/screenshots/ and previewed here.');
                speakDemoResponse('Snapshot recorded, sir.');
            }, 300);
            break;
        case 'mute':
            appendMessage('assistant', 'Workstation master audio toggled.');
            speakDemoResponse('Audio toggled.');
            break;
        case 'notes':
            appendMessage('assistant', 'Displaying active directives: 1. Deploy Mark VII to GitHub Pages. 2. Verify Windows voice automation.');
            speakDemoResponse('Displaying active directives, sir.');
            break;
        case 'lock':
            appendMessage('assistant', 'Workstation lockdown protocol armed.');
            speakDemoResponse('Security protocol armed.');
            break;
    }
}

function speakDemoResponse(text) {
    updateState('SPEAKING');
    targetRMS = 0.75;

    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;

        const voices = window.speechSynthesis.getVoices();
        const britishVoice = voices.find(v => v.lang.includes('en-GB')) || voices.find(v => v.lang.includes('en'));
        if (britishVoice) utterance.voice = britishVoice;

        utterance.onend = () => {
            targetRMS = 0;
            updateState('STANDBY');
        };
        utterance.onerror = () => {
            targetRMS = 0;
            updateState('STANDBY');
        };

        window.speechSynthesis.speak(utterance);
    } else {
        setTimeout(() => {
            targetRMS = 0;
            updateState('STANDBY');
        }, Math.min(4000, text.length * 60));
    }
}

// Browser Web Speech Recognition support
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let browserRecognizer = null;
if (SpeechRecognition) {
    try {
        browserRecognizer = new SpeechRecognition();
        browserRecognizer.continuous = false;
        browserRecognizer.interimResults = false;
        browserRecognizer.lang = 'en-US';

        browserRecognizer.onstart = () => {
            updateState('LISTENING');
        };

        browserRecognizer.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'user_input', text: transcript }));
            }
        };

        browserRecognizer.onerror = (err) => {
            console.log('[Browser Speech Error]:', err);
            updateState('STANDBY');
        };

        browserRecognizer.onend = () => {
            if (currentState === 'LISTENING') {
                updateState('STANDBY');
            }
        };
    } catch (e) {
        console.warn('Browser speech recognition not available:', e);
    }
}

function triggerListening() {
    if (browserRecognizer) {
        try {
            browserRecognizer.start();
        } catch (e) {
            // Already started or busy
        }
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'trigger_mic' }));
    }
}

reactorTrigger.addEventListener('click', triggerListening);
micBtn.addEventListener('click', triggerListening);

diagBtn.addEventListener('click', () => sendQuickAction('telemetry'));
snapBtn.addEventListener('click', () => sendQuickAction('screenshot'));
muteBtn.addEventListener('click', () => sendQuickAction('mute'));
notesBtn.addEventListener('click', () => sendQuickAction('notes'));
lockBtn.addEventListener('click', () => sendQuickAction('lock'));

// Circular Visualizer Canvas Rendering
let angleOffset = 0;
function renderVisualizer() {
    requestAnimationFrame(renderVisualizer);

    // Smooth RMS interpolation
    currentRMS += (targetRMS - currentRMS) * 0.2;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 105;

    ctx.clearRect(0, 0, width, height);

    angleOffset += 0.01;
    const barCount = 48;
    const angleStep = (Math.PI * 2) / barCount;

    for (let i = 0; i < barCount; i++) {
        const angle = i * angleStep + angleOffset;
        
        // Compute wave amplitude
        const noise = Math.sin(i * 0.8 + angleOffset * 4) * 0.5 + 0.5;
        let barHeight = 6 + (currentRMS * 45 * noise);

        if (currentState === 'LISTENING') {
            barHeight = 10 + (Math.sin(i * 0.5 + angleOffset * 6) * 15 * Math.max(currentRMS, 0.4));
        }

        const x1 = centerX + Math.cos(angle) * radius;
        const y1 = centerY + Math.sin(angle) * radius;
        const x2 = centerX + Math.cos(angle) * (radius + barHeight);
        const y2 = centerY + Math.sin(angle) * (radius + barHeight);

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.lineWidth = 2.5;

        if (currentState === 'LISTENING') {
            ctx.strokeStyle = `rgba(0, 255, 170, ${0.4 + currentRMS * 0.6})`;
            ctx.shadowColor = '#00ffaa';
        } else if (currentState === 'SPEAKING') {
            ctx.strokeStyle = (i % 2 === 0) 
                ? `rgba(0, 240, 255, ${0.5 + currentRMS * 0.5})` 
                : `rgba(255, 183, 0, ${0.5 + currentRMS * 0.5})`;
            ctx.shadowColor = '#00f0ff';
        } else {
            ctx.strokeStyle = `rgba(0, 240, 255, ${0.15 + Math.sin(angleOffset + i) * 0.1})`;
            ctx.shadowColor = '#00f0ff';
        }

        ctx.shadowBlur = 8;
        ctx.stroke();
    }
}

renderVisualizer();
connectWebSocket();
