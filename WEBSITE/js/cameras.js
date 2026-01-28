const cameras = [
    {
        id: 1,
        name: 'CAM-01 (Gate)',
        ip: '192.168.1.101',
        status: 'online',
        ai: true,
        // I define the overlay configuration here to map physical hazards to the camera's viewport.
        locationLabel: 'North Gate',
        hazards: [
            { type: 'PERSON', severity: 'critical', x: 20, y: 30, w: 15, h: 35 } // Percentage-based positioning for responsive scaling
        ],
        evacPoint: null
    },
    {
        id: 2,
        name: 'CAM-02 (Perimeter)',
        ip: '192.168.1.102',
        status: 'online',
        ai: true,
        locationLabel: 'West Perimeter',
        hazards: [], // Safe
        evacPoint: { label: 'Assembly Point B', x: 75, y: 60 } // Visible evacuation marker
    },
    {
        id: 3,
        name: 'CAM-03 (Hallway)',
        ip: '192.168.1.103',
        status: 'offline',
        ai: false,
        locationLabel: 'Main Hall',
        hazards: [],
        evacPoint: { label: 'Exit 2', x: 50, y: 80 }
    }
];

/**
 * I structured this render loop to dynamically build the camera grid.
 * It handles the complex overlay logic (hazards, evac points) in a single pass.
 */
function renderCameras() {
    const grid = document.getElementById('camera-grid');
    grid.innerHTML = '';

    cameras.forEach(cam => {
        const card = document.createElement('div');
        card.className = 'card';

        // Building the overlay container
        let overlays = `<div class="camera-overlay-container">`;

        // 1. Camera Location Badge - I ensured this overlay is always visible for context.
        overlays += `
            <div class="overlay-cam-loc">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                ${cam.locationLabel}
            </div>
        `;

        // 2. Hazard Zones - I only render these if the camera is online to avoid ghost data.
        if (cam.status === 'online' && cam.hazards) {
            cam.hazards.forEach(h => {
                overlays += `
                    <div class="overlay-hazard-zone" style="left: ${h.x}%; top: ${h.y}%; width: ${h.w}%; height: ${h.h}%;">
                        <div class="overlay-hazard-label">${h.type} (${h.severity})</div>
                    </div>
                `;
            });
        }

        // 3. Evacuation Points - I layered this logic to assist in route planning.
        if (cam.status === 'online' && cam.evacPoint) {
            overlays += `
                <div class="overlay-evac-point" style="left: ${cam.evacPoint.x}%; top: ${cam.evacPoint.y}%;">
                    <div class="evac-marker-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
                    </div>
                    <div class="evac-marker-label">${cam.evacPoint.label}</div>
                </div>
            `;
        }

        overlays += `</div>`;

        // I constructed the card HTML here, using my 'status-badge' component for uniformity.
        card.innerHTML = `
            <div class="card-header">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>${cam.name}</span>
                    ${cam.ai ? '<span class="status-badge" style="font-size:0.7em; padding: 2px 6px;">AI ACTIVE</span>' : ''}
                </div>
                <span class="status-badge ${cam.status}">
                    <span style="width:8px; height:8px; background: currentColor; border-radius:50%;"></span>
                    ${cam.status.toUpperCase()}
                </span>
            </div>
            <div class="camera-view" style="aspect-ratio: 16/9; background: #000; position: relative;">
                ${cam.status === 'online' ?
                `<!-- I use a placeholder here for the MJPEG stream, but the overlay logic handles the real data -->
                     <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #333;">
                        [ VIDEO STREAM ]
                     </div>
                     ${overlays}
                    `
                :
                `<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color: var(--accent-cricital);">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><desc>Download more icon styles at https://icons8.com</desc><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                        <span style="margin-top: 1rem;">SIGNAL LOST</span>
                     </div>`
            }
                ${cam.status === 'online' ? '<div class="live-badge" style="z-index: 20;">LIVE</div>' : ''}
            </div>
            <div class="card-body" style="padding: 0.5rem 1rem; border-top: 1px solid var(--border-color);">
                <div class="flex-between">
                    <span class="text-muted text-sm">Target: ${cam.locationLabel}</span>
                    <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="expandCamera(${cam.id})">Expand</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

/**
 * simple expand handler.
 */
function expandCamera(id) {
    alert(`Expand request for Camera ${id}`);
}

/**
 * I implemented this to simulate a stream refresh without a full page reload.
 */
function refreshStreams() {
    const grid = document.getElementById('camera-grid');
    grid.style.opacity = '0.5';
    setTimeout(() => {
        grid.style.opacity = '1';
        renderCameras(); // I trigger a re-render to update the state.
    }, 500);
}

// I kick off the render process once the DOM is ready.
document.addEventListener('DOMContentLoaded', renderCameras);
