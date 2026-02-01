/**
 * MOD-EVAC-MS - Dashboard Page Script
 * I architected this module to handle real-time sensor data visualization and system status monitoring.
 * It's designed to be the central nervous system of the user interface.
 */

// I explicitly cache these DOM elements to avoid expensive querySelector lookups during high-frequency update loops.
let elements = {};

/**
 * I structured this initialization to run immediately upon load, binding all necessary DOM elements
 * and establishing the event subscription model with the API layer.
 */
function initDashboard() {
    elements = {
        waterLevel: document.getElementById('water-level'),
        gyroX: document.getElementById('gyro-x'),
        gyroY: document.getElementById('gyro-y'),
        gyroZ: document.getElementById('gyro-z'),
        alertStatus: document.getElementById('alert-status'),
        alertBadge: document.querySelector('.status-badge'),
        cameraFeeds: document.querySelectorAll('.camera-view'),
        recentActivity: document.querySelector('.list-group')
    };

    // I implemented this check to ensure the API is fully loaded before we attempt to subscribe.
    // If there's a race condition, it retries in 100ms.
    if (typeof API === 'undefined') {
        setTimeout(initDashboard, 100);
        return;
    }

    // I utilize a pub/sub pattern here to decouple the UI updates from the data fetching logic.
    API.on('sensor', updateSensorDisplay);
    API.on('alert', updateAlertDisplay);
    API.on('detection', addActivityItem);
    API.on('connect', () => updateConnectionStatus(true));
    API.on('disconnect', () => updateConnectionStatus(false));

    console.log('[Dashboard] I successfully initialized the dashboard controller.');
}

/**
 * I designed this function to efficiently update the sensor display.
 * It strictly checks for data integrity before touching the DOM to prevent rendering errors.
 */
function updateSensorDisplay(data) {
    if (!data) return;

    // Water level logic
    if (elements.waterLevel && data.water !== undefined) {
        const level = data.water.toFixed(1);
        elements.waterLevel.textContent = `${level}%`;

        // I implemented progressive color warnings here to give immediate visual feedback on severity.
        if (data.water > 70) {
            elements.waterLevel.style.color = 'var(--accent-cricital)';
        } else if (data.water > 40) {
            elements.waterLevel.style.color = 'var(--accent-warning)';
        } else {
            elements.waterLevel.style.color = 'var(--accent-success)';
        }
    }

    // Gyroscope telemetry
    if (data.gyro) {
        if (elements.gyroX) elements.gyroX.textContent = data.gyro.x?.toFixed(2) || '0.00';
        if (elements.gyroY) elements.gyroY.textContent = data.gyro.y?.toFixed(2) || '0.00';
        if (elements.gyroZ) elements.gyroZ.textContent = data.gyro.z?.toFixed(2) || '0.00';
    }
}

/**
 * This is the critical alert visualization logic.
 * I map the raw integer states to human-readable statuses and color codes.
 */
function updateAlertDisplay(data) {
    if (!data) return;

    // I defined these constants to match the backend firmware state machine.
    const alertNames = ['SAFE', 'CALLING', 'MESSAGING', 'DANGER', 'EVACUATE'];
    const alertColors = {
        'SAFE': 'var(--accent-success)',
        'CALLING': 'var(--accent-warning)',
        'MESSAGING': 'var(--accent-primary)',
        'DANGER': 'var(--accent-cricital)',
        'EVACUATE': 'var(--accent-cricital)'
    };

    const stateName = data.state || alertNames[data.value] || 'UNKNOWN';

    if (elements.alertStatus) {
        elements.alertStatus.textContent = stateName;
        elements.alertStatus.style.color = alertColors[stateName] || 'var(--text-primary)';
    }

    // Status Badge Logic
    if (elements.alertBadge) {
        elements.alertBadge.className = 'status-badge';
        if (stateName === 'SAFE') {
            elements.alertBadge.classList.add('online');
            elements.alertBadge.innerHTML = '<span>●</span> System Online';
        } else if (stateName === 'DANGER' || stateName === 'EVACUATE') {
            elements.alertBadge.style.color = 'var(--accent-cricital)';
            elements.alertBadge.innerHTML = `<span>●</span> ${stateName}`;
        } else {
            elements.alertBadge.style.color = 'var(--accent-warning)';
            elements.alertBadge.innerHTML = `<span>●</span> ${stateName}`;
        }
    }
}

/**
 * I process incoming detection events here.
 * I limit the list to the last 10 items to prevent memory leaks in long-running sessions.
 */
function addActivityItem(data) {
    if (!elements.recentActivity) return;

    const time = new Date().toLocaleTimeString();
    const className = data.class || 'Detection';
    const confidence = ((data.confidence || 0) * 100).toFixed(0);

    // I categorize threats into critical and warning tiers for rapid assessment.
    const critical = ['Fire', 'Explosion', 'Flood', 'Collapsed Structure'];
    const warning = ['Smoke', 'Falling Debris', 'Landslide'];

    let alertClass = 'alert-info';
    if (critical.includes(className)) {
        alertClass = 'alert-critical';
    } else if (warning.includes(className)) {
        alertClass = 'alert-warning';
    }

    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
        <div class="alert-indicator ${alertClass}"></div>
        <div style="flex: 1;">
            <div class="flex-between">
                <strong>${className} Detected</strong>
                <span class="text-muted text-sm">${time}</span>
            </div>
            <div class="text-muted text-sm">ESP32-CAM • Confidence ${confidence}%</div>
        </div>
    `;

    // I insert new items at the top for immediate visibility (LIFO).
    elements.recentActivity.insertBefore(item, elements.recentActivity.firstChild);

    // Garbage collection for the UI.
    while (elements.recentActivity.children.length > 10) {
        elements.recentActivity.removeChild(elements.recentActivity.lastChild);
    }
}

/**
 * Simple connection state feedback.
 */
function updateConnectionStatus(connected) {
    const statusBadge = document.querySelector('.status-badge');
    if (statusBadge) {
        if (connected) {
            statusBadge.classList.add('online');
        } else {
            statusBadge.classList.remove('online');
        }
    }
}

// I ensure the script only executes once the DOM is fully constructed.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
