// I updated this to fetch live cameras from the backend instead of using placeholders.
let cameras = [];

/**
 * I structured this to fetch the actual device list from the server.
 * This ensures that when a new ESP32-CAM registers, it appears here automatically.
 */
async function fetchCameras() {
    try {
        const response = await fetch('/api/devices');
        const data = await response.json();

        // Transform the system devices into camera objects
        cameras = data.devices
            .filter(d => d.device_type === 'esp32_cam' || d.device_type === 'camera')
            .map(d => ({
                id: d.device_id,
                name: d.device_id.replace(/_/g, ' '),
                ip: d.port || 'Unknown',
                status: d.connected ? 'online' : 'offline',
                ai: true,
                locationLabel: d.location || 'Surveillance Zone',
                hazards: [],
                evacPoint: null
            }));

        renderCameras();
    } catch (e) {
        console.error("Failed to fetch cameras:", e);
    }
}

/**
 * I added this sync loop to update hazard overlays in real-time.
 * It polls the system status to see if the AI has detected anything.
 */
async function syncHazards() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        const detections = status.detections || [];

        cameras.forEach(cam => {
            // Filter detections for this specific camera
            // In a multi-camera setup, 'device_id' in detection would match cam.id
            cam.hazards = detections.map(det => ({
                type: det.class.toUpperCase(),
                severity: det.confidence > 0.8 ? 'critical' : 'warning',
                x: det.bbox[0] / 6.4, // Map VGA 640 to %
                y: det.bbox[1] / 4.8, // Map VGA 480 to %
                w: (det.bbox[2] - det.bbox[0]) / 6.4,
                h: (det.bbox[3] - det.bbox[1]) / 4.8
            }));
        });

        renderCameras();
    } catch (e) {
        // Silently fail sync
    }
}

/**
 * I structured this render loop to dynamically build the camera grid.
 * It handles the complex overlay logic (hazards, evac points) in a single pass.
 */
function renderCameras() {
    const grid = document.getElementById('camera-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (cameras.length === 0) {
        grid.innerHTML = '<div class="text-muted" style="grid-column: 1/-1; text-align: center; padding: 4rem;">Searching for active cameras...</div>';
        return;
    }

    cameras.forEach(cam => {
        const card = document.createElement('div');
        card.className = 'card';

        // Building the overlay container
        let overlays = `<div class="camera-overlay-container">`;

        // 1. Camera Location Badge
        overlays += `
            <div class="overlay-cam-loc">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                ${cam.locationLabel}
            </div>
        `;

        // 2. Hazard Zones
        if (cam.status === 'online' && cam.hazards) {
            cam.hazards.forEach(h => {
                overlays += `
                    <div class="overlay-hazard-zone ${h.severity}" style="left: ${h.x}%; top: ${h.y}%; width: ${h.w}%; height: ${h.h}%;">
                        <div class="overlay-hazard-label">${h.type}</div>
                    </div>
                `;
            });
        }

        overlays += `</div>`;

        // Video Stream URL (Proxied through backend to provide flip and AI processing)
        const streamUrl = `/api/camera/${cam.id}/stream`;

        card.innerHTML = `
            <div class="card-header">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>${cam.name}</span>
                    <span class="status-badge" style="font-size:0.7em; padding: 2px 6px; background: #222;">ID: ${cam.id}</span>
                </div>
                <span class="status-badge ${cam.status}">
                    <span style="width:8px; height:8px; background: currentColor; border-radius:50%;"></span>
                    ${cam.status.toUpperCase()}
                </span>
            </div>
            <div class="camera-view" style="aspect-ratio: 16/9; background: #000; position: relative; overflow: hidden;">
                ${cam.status === 'online' ?
                `<img src="${streamUrl}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.src='/img/no-signal.png'"/>
                 ${overlays}`
                :
                `<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color: var(--accent-critical);">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                        <span style="margin-top: 1rem;">SIGNAL LOST</span>
                     </div>`
            }
            </div>
            <div class="card-body" style="padding: 0.5rem 1rem; border-top: 1px solid var(--border-color);">
                <div class="flex-between">
                    <span class="text-muted text-sm">${cam.ip}</span>
                    <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="location.href='ai.html'">AI View</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function refreshStreams() {
    fetchCameras();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    fetchCameras();
    // Refresh list every 10 seconds
    setInterval(fetchCameras, 10000);
    // Sync hazards every 1 second
    setInterval(syncHazards, 1000);
});

