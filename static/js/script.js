// --- HARDWARE TELEMETRY ENGINE (CANVAS) ---
class HardwareSimulator {
    constructor(canvasId, color, min, max) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.color = color;
        this.data = new Array(60).fill(min);
        this.min = min;
        this.max = max;
        this.target = min;
        this.current = min;
        
        // Handle High-DPI displays for sharp canvas
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.width = rect.width;
        this.height = rect.height;
    }

    setTarget(val) { this.target = val; }

    update() {
        // Smoothly interpolate towards the target value (easing)
        this.current += (this.target - this.current) * 0.1;
        
        // Add slight random noise to make it look alive
        let noise = (Math.random() - 0.5) * ((this.max - this.min) * 0.05);
        let val = Math.max(this.min, Math.min(this.max, this.current + noise));
        
        this.data.push(val);
        this.data.shift();
        this.draw();
    }

    draw() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.color;
        this.ctx.lineWidth = 1.5;
        this.ctx.shadowBlur = 8;
        this.ctx.shadowColor = this.color;

        for (let i = 0; i < this.data.length; i++) {
            let x = (i / (this.data.length - 1)) * this.width;
            // Normalize Y based on min/max
            let normalizedY = (this.data[i] - this.min) / (this.max - this.min);
            let y = this.height - (normalizedY * this.height * 0.8) - (this.height * 0.1); 

            if (i === 0) this.ctx.moveTo(x, y);
            else this.ctx.lineTo(x, y);
        }
        this.ctx.stroke();
    }
}

// Initialize Canvases
const tempSim = new HardwareSimulator('tempChart', '#4ae8c4', 35, 95); // 35C to 95C
const speedSim = new HardwareSimulator('speedChart', '#d2a8ff', 0, 4.2); // 0 to 4.2 GHz

// Animation Loop for Telemetry
function renderTelemetry() {
    tempSim.update();
    speedSim.update();
    requestAnimationFrame(renderTelemetry);
}
renderTelemetry();

// --- UI CONTROLLERS ---
function switchDataTab(event, tabId) {
    document.querySelectorAll('.data-stream').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('bank-' + tabId).classList.add('active');
    event.currentTarget.classList.add('active');
}

function startSwarm() {
    const btn = document.getElementById('runBtn');
    
    // UI Elements
    const termMain = document.getElementById('terminal');
    const bankBlue = document.getElementById('bank-blueprint');
    const bankCode = document.getElementById('bank-code');
    const bankError = document.getElementById('bank-errors');
    
    const vramBar = document.getElementById('vramBar');
    const vramValue = document.getElementById('vramValue');
    const tempValue = document.getElementById('tempValue');
    const speedValue = document.getElementById('speedValue');
    
    const rawPrompt = document.getElementById('promptInput').value;
    const rawArgs = document.getElementById('argsInput').value;

    if (!rawPrompt.trim()) {
        alert("ERR: Missing directive architecture.");
        return;
    }

    // Initialize Run State
    termMain.innerHTML = "<span class='log-sys'>[SEQ.START] UPLINK ESTABLISHED. ENGAGING SWARM...</span><br>";
    bankBlue.innerHTML = ""; bankCode.innerHTML = ""; bankError.innerHTML = "";
    
    btn.disabled = true;
    btn.innerText = "EXECUTING...";
    
    // Hardware State: Booting LLaMA
    vramBar.style.width = "40%";
    vramValue.innerText = "3,210 MB";
    tempSim.setTarget(55); // Temp rises
    speedSim.setTarget(1.2);
    tempValue.innerText = "55 °C";
    speedValue.innerText = "1.2 THz";

    const encodedPrompt = encodeURIComponent(rawPrompt);
    const encodedArgs = encodeURIComponent(rawArgs);
    const eventSource = new EventSource(`/stream/?prompt=${encodedPrompt}&args=${encodedArgs}`);

    let captureState = "none"; 

    eventSource.onmessage = function(event) {
        if (event.data === "[DONE]") {
            eventSource.close();
            resetUIState();
            termMain.innerHTML += "<br><span class='log-sys'>[EOF] PIPELINE CLOSED.</span><br>";
            termMain.scrollTop = termMain.scrollHeight;
            return;
        }

        let rawData = event.data;
        let formattedData = rawData;
        
        // --- DYNAMIC TELEMETRY INTERCEPTS ---
        if (rawData.includes("LLaMA unloaded")) {
            // Swap to Qwen (Heavier model)
            vramBar.style.width = "85%";
            vramValue.innerText = "6,840 MB";
            tempSim.setTarget(72);
            tempValue.innerText = "72 °C";
        }
        if (rawData.includes("Compiling in Docker")) {
            // Container Execution Spike
            speedSim.setTarget(4.1);
            speedValue.innerText = "4.1 THz";
            tempSim.setTarget(85);
            tempValue.innerText = "85 °C";
        }
        
        // --- STYLING ---
        if (rawData.includes("[SYSTEM]")) {
            formattedData = `<span class="log-sys">${formattedData}</span>`;
        } else if (rawData.includes("BLUEPRINT :")) {
            formattedData = `<span class="log-accent">${formattedData}</span>`;
        } else if (rawData.includes("SUCCESS") || rawData.includes("GENERATED C++ CODE")) {
            formattedData = `<span class="log-success">${formattedData}</span>`;
        } else if (rawData.includes("FAILED") || rawData.includes("ERROR") || rawData.includes("[!]")) {
            formattedData = `<span class="log-error">${formattedData}</span>`;
            // Temp spike on error panic
            tempSim.setTarget(88);
            tempValue.innerText = "88 °C";
        }

        // --- MASTER TERMINAL ---
        termMain.innerHTML += formattedData;
        termMain.scrollTop = termMain.scrollHeight;

        // --- ROUTING MEMORY BANKS ---
        if (rawData.includes("HERE IS THE BLUEPRINT :")) captureState = "blueprint";
        else if (rawData.includes("=== GENERATED C++ CODE ===")) captureState = "code";
        else if (rawData.includes("COMPILER ERROR") || rawData.includes("RUNTIME CRASH")) captureState = "error";

        if (captureState === "blueprint") {
            bankBlue.innerHTML += formattedData;
            bankBlue.scrollTop = bankBlue.scrollHeight;
        } else if (captureState === "code") {
            bankCode.innerHTML += formattedData;
            bankCode.scrollTop = bankCode.scrollHeight;
        } else if (captureState === "error") {
            bankError.innerHTML += formattedData;
            bankError.scrollTop = bankError.scrollHeight;
        }

        if (rawData.includes("LLaMA unloaded") || rawData.includes("==========================") || rawData.includes("----------------------")) {
            captureState = "none";
        }
    };

    eventSource.onerror = function() {
        termMain.innerHTML += "<br><span class='log-error'>[FATAL] UPLINK SEVERED.</span><br>";
        eventSource.close();
        resetUIState();
    };

    function resetUIState() {
        btn.disabled = false;
        btn.innerText = "TRANSMIT DIRECTIVE";
        
        // Hardware Cool Down
        vramBar.style.width = "5%";
        vramValue.innerText = "412 MB";
        tempSim.setTarget(42);
        speedSim.setTarget(0.1);
        tempValue.innerText = "42 °C";
        speedValue.innerText = "0.1 THz";
    }
} // <--- THIS BRACE CLOSES startSwarm()!

// ==========================================
// GLOBAL SCOPE: ARCHIVE FUNCTION
// ==========================================
async function loadArchive() {
    const archivePane = document.getElementById('bank-archive');
    archivePane.innerHTML = "<span class='log-sys'>[NET] Fetching orbital records...</span><br>";

    try {
        const response = await fetch('/archive/');
        const data = await response.json();
        archivePane.innerHTML = "";
        
        if (data.archives.length === 0) {
            archivePane.innerHTML = "<span class='muted'>No records found in database.</span>";
            return;
        }

        data.archives.forEach(log => {
            const statusColor = log.status === 'SUCCESS' ? 'var(--accent)' : 'var(--alert)';
            archivePane.innerHTML += `
                <div style="border: 1px solid var(--border-dim); padding: 1rem; margin-bottom: 1rem; background: rgba(0,0,0,0.4);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; border-bottom: 1px solid var(--border-dim); padding-bottom: 0.5rem;">
                        <span style="color: ${statusColor}; font-weight: bold; font-family: 'Chakra Petch';">[${log.status}]</span>
                        <span class="muted" style="font-size: 0.7rem;">${log.date}</span>
                    </div>
                    <div style="color: var(--text-main); font-size: 0.8rem; margin-bottom: 0.5rem;">
                        <strong style="color: var(--text-muted);">TARGET:</strong> ${log.prompt} <br><br>
                        <strong style="color: var(--text-muted);">VECTORS:</strong> <span class="hl-text">${log.args || 'NULL'}</span>
                    </div>
                    <textarea readonly style="width: 100%; height: 100px; font-size: 0.7rem; margin-top: 10px; background: #020305; color: var(--accent); border: 1px solid var(--border-dim);">${log.code}</textarea>
                </div>
            `;
        });
    } catch(e) {
        archivePane.innerHTML = "<span class='log-error'>[FATAL] Archive link offline.</span><br>";
    }
}