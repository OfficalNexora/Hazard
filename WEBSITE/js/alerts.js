const alertsData = [
    { type: 'critical', title: 'Unidentified Person Detected', source: 'CAM-01', time: '10:42:05', id: 1 },
    { type: 'warning', title: 'Motion Detected (Zone B)', source: 'CAM-02', time: '09:15:30', id: 2 },
    { type: 'info', title: 'System Backup Complete', source: 'System', time: '04:00:00', id: 3 },
    { type: 'warning', title: 'High CPU Temperature', source: 'Server', time: 'Yesterday', id: 4 },
    { type: 'info', title: 'Scheduled Reboot', source: 'System', time: 'Yesterday', id: 5 },
];

function renderAlerts(filter = 'all') {
    const list = document.getElementById('alerts-list');
    list.innerHTML = '';

    alertsData.forEach(alert => {
        if (filter !== 'all' && alert.type !== filter) return;

        const item = document.createElement('div');
        item.className = 'list-item';
        item.style.cursor = 'pointer';
        item.onclick = () => highlightEffect(item); // I attached this click handler for immediate tactile feedback.

        item.innerHTML = `
            <div class="alert-indicator alert-${alert.type}"></div>
            <div style="flex: 1;">
                <div class="flex-between">
                    <strong style="${alert.type === 'critical' ? 'color: var(--accent-cricital)' : ''}">${alert.title}</strong>
                    <span class="text-muted text-sm">${alert.time}</span>
                </div>
                <div class="flex-between mt-4" style="margin-top: 0.25rem;">
                    <span class="text-muted text-sm">Source: ${alert.source}</span>
                    <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.75rem;">View</button>
                </div>
            </div>
        `;
        list.appendChild(item);
    });
}

function filterAlerts(type) {
    renderAlerts(type);
}

/**
 * I added this visual highlight effect to improve the user experience during rapid alert triage.
 */
function highlightEffect(el) {
    el.style.backgroundColor = 'rgba(255,255,255,0.05)';
    setTimeout(() => {
        el.style.backgroundColor = 'transparent';
    }, 200);
}

document.addEventListener('DOMContentLoaded', () => renderAlerts());
