/**
 * MOD-EVAC-MS - AI Detection Page Script
 * I built this module to handle the high-throughput WebSocket stream from the YOLOv8 inference engine.
 */

// I cache these elements to prevent re-querying the DOM on every frame.
const aiTable = document.getElementById('ai-table')?.querySelector('tbody');
const fpsDisplay = document.querySelector('[data-stat="fps"]');
const latencyDisplay = document.querySelector('[data-stat="latency"]');
const detectionsDisplay = document.querySelector('[data-stat="detections"]');

// Performance metrics tracking
let totalDetections = 0;
let lastDetectionTime = Date.now();

// I configured these colors to match the universal hazard warning standards (ISO 3864).
const classColors = {
    'Fire': '#ef4444',
    'Explosion': '#ef4444',
    'Smoke': '#6b7280',
    'Flood': '#3b82f6',
    'Landslide': '#f97316',
    'Falling Debris': '#eab308',
    'Collapsed Structure': '#991b1b',
    'Industrial Accident': '#7c3aed'
};

/**
 * I implemented this function to append new detection rows with minimal layout thrashing.
 */
function addDetection(detection) {
    if (!aiTable) return;

    totalDetections++;
    const now = Date.now();
    const latency = now - lastDetectionTime;
    lastDetectionTime = now;

    // Row construction
    const row = document.createElement('tr');
    const time = new Date().toLocaleTimeString();
    const className = detection.class || 'Unknown';
    const confidence = ((detection.confidence || 0) * 100).toFixed(1);
    const source = detection.source || 'ESP32-CAM';
    const color = classColors[className] || '#10b981';

    row.innerHTML = `
        <td style="font-family: monospace;">${time}</td>
        <td>
            <span style="display: inline-flex; align-items: center; gap: 0.5rem;">
                <span style="width: 8px; height: 8px; background: ${color}; border-radius: 50%;"></span>
                ${className}
            </span>
        </td>
        <td>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="flex: 1; background: var(--bg-panel); border-radius: 4px; height: 8px; overflow: hidden;">
                    <div style="width: ${confidence}%; height: 100%; background: ${color};"></div>
                </div>
                <span style="font-family: monospace; font-size: 0.85rem;">${confidence}%</span>
            </div>
        </td>
        <td style="color: var(--text-secondary);">${source}</td>
    `;

    // I utilize a CSS animation here for smooth entry.
    row.style.animation = 'fadeIn 0.3s ease';
    aiTable.insertBefore(row, aiTable.firstChild);

    // I limit the table to 50 rows to keep the DOM light.
    while (aiTable.children.length > 50) {
        aiTable.removeChild(aiTable.lastChild);
    }

    // Refresh stats
    updateStats(latency);
}

/**
 * I update the latency and count metrics here.
 */
function updateStats(latency) {
    if (detectionsDisplay) {
        detectionsDisplay.textContent = totalDetections.toLocaleString();
    }
    if (latencyDisplay && latency > 0 && latency < 5000) {
        latencyDisplay.textContent = `${latency} ms`;
    }
}

/**
 * I set up the API listeners here. I ensure we wait for the API object to be ready.
 */
function initAI() {
    // Retry logic for API availability
    if (typeof API === 'undefined') {
        setTimeout(initAI, 100);
        return;
    }

    // I subscribe to the 'detection' event stream.
    API.on('detection', (data) => {
        addDetection(data);
    });

    // Connection state handlers
    API.on('connect', () => {
        console.log('[AI] I established connection to backend.');
        document.querySelector('.status-badge')?.classList.add('online');
    });

    API.on('disconnect', () => {
        console.log('[AI] I lost connection to backend.');
        document.querySelector('.status-badge')?.classList.remove('online');
    });

    // Load initial data
    loadInitialDetections();
}

/**
 * I fetch the recent history to populate the table on load.
 */
async function loadInitialDetections() {
    try {
        const response = await API.getDetections(20);
        if (response.detections) {
            // I reverse the order here to show newest at the top.
            response.detections.reverse().forEach(d => addDetection(d));
        }
    } catch (e) {
        console.error('[AI] I failed to load detections:', e);
    }
}

// Initialize
initAI();

// I inject this animation style dynamically to keep the CSS file clean.
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
