// ============================================================
// MAP.JS - Automatic Location & Live Tracking System
// I architected this module to handle precise geolocation and map rendering using Leaflet.js
// ============================================================

const MAP_CONFIG = {
    initialCenter: [14.5998, 120.9842], // Fallback center
    initialZoom: 18,
    minZoom: 15,
    maxZoom: 20
};

// I keep this state clean for production; no demo artifacts allowed.
const ESP_ENDPOINTS = [];
const HAZARDS = [];
const EVAC_POINTS = [];

let map = null;
let isOnline = true;
let tileLayer = null;
let serverMarker = null;

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    startSystemInitialization();
});

async function startSystemInitialization() {
    // I check for a persisted location lock first to avoid redundant GPS polling.
    const savedLocation = getSavedPosition();

    if (savedLocation) {
        // Location already triangulated - use it
        document.getElementById('location-overlay').style.display = 'none';
        initMap(savedLocation);
    } else {
        // I need to perform a full hardware triangulation if no lock exists.
        document.getElementById('location-overlay').innerHTML = `
            <div style="text-align: center; color: var(--text-primary);">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📡</div>
                <h2 style="margin-bottom: 0.5rem;">Precise System Calibration</h2>
                <p style="max-width: 400px; color: var(--text-secondary); margin-bottom: 1rem;">
                    Acquiring high-precision GPS lock...
                </p>
                <div id="calibration-status" style="color: var(--accent-primary); margin-bottom: 1rem;">
                    Waiting for satellite lock...
                </div>
                <div id="calibration-progress" style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 10px; width: 300px; margin: 0 auto; overflow:hidden;">
                    <div id="calibration-bar" style="background: var(--accent-primary); width: 0%; height: 100%; transition: width 0.3s ease;"></div>
                </div>
            </div>
        `;

        // Start GPS-only calibration
        performAutoCalibration();
    }
}

// ============================================================
// GPS-ONLY LOCATION DETECTION
// ============================================================

async function performAutoCalibration() {
    const statusEl = document.getElementById('calibration-status');
    const barEl = document.getElementById('calibration-bar');

    // I intentionally removed IP Geolocation here to force hardware-level accuracy.

    statusEl.textContent = 'Triangulating GPS position...';
    barEl.style.width = '30%';

    try {
        const gpsLocation = await performGPSTriangulation();

        if (gpsLocation) {
            barEl.style.width = '100%';
            statusEl.textContent = 'Position Locked.';

            const finalPosition = {
                lat: gpsLocation.lat,
                lng: gpsLocation.lng,
                accuracy: gpsLocation.accuracy,
                sources: 'GPS-HIGH-PRECISION'
            };

            localStorage.setItem('monitoring_station_location', JSON.stringify(finalPosition));

            await new Promise(r => setTimeout(r, 500));
            document.getElementById('location-overlay').style.display = 'none';
            initMap(finalPosition);
        }
    } catch (e) {
        console.warn('[Location] GPS triangulation failed:', e);
        statusEl.textContent = 'GPS Lock Failed. Retrying...';
        setTimeout(performAutoCalibration, 2000);
    }
}

function performGPSTriangulation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation not supported'));
            return;
        }

        const samples = [];
        const MAX_SAMPLES = 5;
        const TIMEOUT = 20000; // 20s total timeout

        const startTime = Date.now();

        const watchId = navigator.geolocation.watchPosition(
            (pos) => {
                // I filter out low accuracy samples (>100m) to ensure pinpoint precision.
                if (pos.coords.accuracy > 100) {
                    return; // Ignore low accuracy samples
                }

                samples.push({
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude,
                    accuracy: pos.coords.accuracy
                });

                const progress = (samples.length / MAX_SAMPLES) * 100;
                const status = document.getElementById('calibration-status');
                const bar = document.getElementById('calibration-bar');

                if (status) status.textContent = `Triangulating... (${samples.length}/${MAX_SAMPLES} High-Acc Samples)`;
                if (bar) bar.style.width = `${30 + (progress * 0.7)}%`;

                if (samples.length >= MAX_SAMPLES) {
                    navigator.geolocation.clearWatch(watchId);

                    // I implement a simple averaging algorithm here to smooth out GPS jitter.
                    let latSum = 0, lngSum = 0;
                    samples.forEach(s => {
                        latSum += s.lat;
                        lngSum += s.lng;
                    });

                    resolve({
                        lat: latSum / samples.length,
                        lng: lngSum / samples.length,
                        accuracy: samples[samples.length - 1].accuracy
                    });
                }
            },
            (err) => {
                console.warn(err);
                // Don't reject immediately, I want to keep trying until timeout.
            },
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
        );

        // Timeout fallback
        setTimeout(() => {
            navigator.geolocation.clearWatch(watchId);
            if (samples.length > 0) {
                // Return whatever we have captured so far.
                let latSum = 0, lngSum = 0;
                samples.forEach(s => { latSum += s.lat; lngSum += s.lng; });
                resolve({
                    lat: latSum / samples.length,
                    lng: lngSum / samples.length,
                    accuracy: samples[samples.length - 1].accuracy
                });
            } else {
                reject(new Error("Timeout waiting for GPS"));
            }
        }, TIMEOUT);
    });
}

// ============================================================
// MAP INITIALIZATION
// ============================================================

function initMap(serverLocation) {
    if (typeof L === 'undefined') {
        document.getElementById('map-container').innerHTML = `
            <div style="display:flex; align-items:center; justify-content:center; height:100%; color:var(--text-secondary);">
                Leaflet JS library not loaded.
            </div>
        `;
        return;
    }

    const center = [serverLocation.lat, serverLocation.lng];

    // I configured the map controls to be minimal for a dashboard view.
    map = L.map('map-container', {
        zoomControl: false,
        attributionControl: false
    }).setView(center, MAP_CONFIG.initialZoom);

    L.control.attribution({ position: 'bottomright' }).addTo(map);

    // Load tiles
    loadTiles();

    // Render server marker
    renderServerMarker(serverLocation);

    // Start Live Tracking (Real-time movement)
    startLiveTracking();
}

// ============================================================
// LIVE TRACKING (STABILIZED & HIGH-PRECISION)
// ============================================================

let locationHistory = [];
const HISTORY_SIZE = 5; // I use a rolling window of 5 points for smoothing.
const JUMP_THRESHOLD_METERS = 50; // I reject any displacement > 50m as a GPS glitch.

function startLiveTracking() {
    if (!navigator.geolocation) return;

    console.log('[System] Starting STABILIZED live tracking...');

    // Watch position permanently
    navigator.geolocation.watchPosition(
        (position) => {
            const rawLat = position.coords.latitude;
            const rawLng = position.coords.longitude;
            const accuracy = position.coords.accuracy;
            const speed = position.coords.speed || 0;

            // 1. FILTER: Ignore low accuracy samples (My Noise Rejection Logic)
            if (accuracy > 50) {
                console.warn(`[Stabilizer] Signal ignored (Too weak: ${accuracy}m)`);
                return;
            }

            // 2. FILTER: Anti-Teleportation (Reject impossible jumps)
            if (locationHistory.length > 0) {
                const lastPos = locationHistory[locationHistory.length - 1];
                const dist = getDistanceInMeters(lastPos.lat, lastPos.lng, rawLat, rawLng);

                // If it moved > 50m in < 2 seconds, it's a glitch (unless moving very fast)
                if (dist > JUMP_THRESHOLD_METERS) {
                    console.warn(`[Stabilizer] Teleport ignored (${dist.toFixed(1)}m jump)`);
                    return;
                }
            }

            // 3. SMOOTHING: Add to history and calculate average
            locationHistory.push({ lat: rawLat, lng: rawLng });
            if (locationHistory.length > HISTORY_SIZE) {
                locationHistory.shift(); // Keep only last N samples
            }

            // Calculate Weighted Average (Favor most recent)
            const smoothed = calculateWeightedAverage(locationHistory);

            // Update Marker Position (Smoothly)
            if (serverMarker) {
                const newLatLng = new L.LatLng(smoothed.lat, smoothed.lng);

                // Leaflet usually handles small moves instantly, but we want it smooth
                serverMarker.setLatLng(newLatLng);

                // I only pan map if user is at edge of screen to avoid dizziness (UX optimization).
                if (!map.getBounds().contains(newLatLng)) {
                    map.panTo(newLatLng);
                }

                // Update Popup with "STABLE" status
                const content = `
                    <div style="min-width: 220px; text-align: center; color: #000;">
                        <strong style="color: #1e40af;">🖥️ MONITORING STATION</strong><br>
                        <div style="font-family: monospace; font-size: 0.85em; margin: 8px 0; background: #e0f2fe; padding: 6px; border-radius: 4px; border: 1px solid #bae6fd;">
                            ${smoothed.lat.toFixed(6)}, ${smoothed.lng.toFixed(6)}
                        </div>
                        <div style="display:flex; justify-content:center; gap:5px; margin-bottom:8px;">
                            <span style="background:#059669; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em;">SIGNAL LOCKED</span>
                            <span style="background:#3b82f6; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em;">STABILIZED</span>
                        </div>
                        <div style="font-size: 0.75em; color: #6b7280;">
                            Hardware Accuracy: ±${Math.round(accuracy)}m<br>
                            Real-Time
                        </div>
                        <div id="debug-stable-stat" style="font-size:0.6em; color:#999; margin-top:5px;">
                            Smoothing ${locationHistory.length} samples...
                        </div>
                    </div>
                `;
                serverMarker.getPopup().setContent(content);
            }
        },
        (error) => {
            console.warn('[Tracking] Location update failed:', error.message);
        },
        {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        }
    );
}

// I implemented this weighted average to reduce processing delay while keeping smoothness.
// Linear weighting: Oldest = 1, Newest = N
function calculateWeightedAverage(history) {
    let latSum = 0, lngSum = 0, weightSum = 0;

    history.forEach((pos, index) => {
        const weight = index + 1;
        latSum += pos.lat * weight;
        lngSum += pos.lng * weight;
        weightSum += weight;
    });

    return {
        lat: latSum / weightSum,
        lng: lngSum / weightSum
    };
}

// Helper: Haversine Distance (My implementation of the standard formula)
function getDistanceInMeters(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // metres
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
        Math.cos(φ1) * Math.cos(φ2) *
        Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
}

function getSavedPosition() {
    const saved = localStorage.getItem('monitoring_station_location');
    if (saved) {
        return JSON.parse(saved);
    }
    return null;
}

// ============================================================
// SERVER MARKER
// ============================================================

function renderServerMarker(location) {
    const serverIcon = L.divIcon({
        className: 'server-location-marker',
        html: `<div style="
            background-color: #3b82f6; 
            width: 18px; 
            height: 18px; 
            border-radius: 50%; 
            border: 3px solid white; 
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.8);
            animation: pulse-glow 2s infinite;
        "></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    serverMarker = L.marker([location.lat, location.lng], {
        icon: serverIcon,
        draggable: false
    }).addTo(map);

    const initialContent = `
        <div style="min-width: 220px; text-align: center; color: #000;">
            <strong style="color: #1e40af;">🖥️ MONITORING STATION</strong><br>
            <div style="font-family: monospace; font-size: 0.85em; margin: 8px 0; background: #f3f4f6; padding: 6px; border-radius: 4px;">
                Initial Lock...
            </div>
        </div>
    `;

    serverMarker.bindPopup(initialContent);
}

window.recalibrateSystem = function () {
    if (confirm("Reset calibration?")) {
        localStorage.removeItem('monitoring_station_location');
        location.reload();
    }
};

// ============================================================
// TILE LOADING
// ============================================================

function loadTiles() {
    if (tileLayer) map.removeLayer(tileLayer);

    if (isOnline) {
        tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // Dark mode filter
        if (document.querySelector('.leaflet-tile-pane')) {
            document.querySelector('.leaflet-tile-pane').style.filter =
                "invert(90%) hue-rotate(180deg) contrast(80%)";
        }
    }
}

window.toggleMapMode = function () {
    isOnline = !isOnline;
    const dot = document.getElementById('map-mode-dot');
    const text = document.getElementById('map-mode-text');

    if (isOnline) {
        dot.style.background = 'var(--accent-success)';
        text.textContent = 'Online Mode';
    } else {
        dot.style.background = 'var(--text-secondary)';
        text.textContent = 'Offline Mode';
    }

    loadTiles();
};
