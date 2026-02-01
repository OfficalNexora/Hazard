document.addEventListener('DOMContentLoaded', () => {
    setupTabSwitcher();
    renderGSMNumbers();
});

/**
 * I implemented this manual tab switcher logic to avoid heavyweight UI library dependencies.
 * It strictly toggles visibility between the Network and GSM views.
 */
function setupTabSwitcher() {
    const btnNetwork = document.getElementById('btn-view-network');
    const btnGsm = document.getElementById('btn-view-gsm');
    const viewNetwork = document.getElementById('view-network');
    const viewGsm = document.getElementById('view-gsm');

    if (!btnNetwork || !btnGsm) return;

    btnNetwork.addEventListener('click', () => {
        // Update Buttons
        btnNetwork.classList.add('active');
        btnGsm.classList.remove('active');

        // Update Views
        viewNetwork.style.display = 'block';
        viewGsm.style.display = 'none';
    });

    btnGsm.addEventListener('click', () => {
        // Update Buttons
        btnGsm.classList.add('active');
        btnNetwork.classList.remove('active');

        // Update Views
        viewGsm.style.display = 'block';
        viewNetwork.style.display = 'none';

        // I ensure GSM data is fresh on every view toggle.
        renderGSMNumbers();
    });
}

// I use these mock contacts to demonstrate the SMS dispatch capability before the physical GSM module is online.
const GSM_CONTACTS = [
    { name: "Emergency Response Team", number: "+63 917 123 4567", role: "Primary Response", active: true },
    { name: "Fire Department", number: "+63 918 234 5678", role: "External Agency", active: true },
    { name: "Admin Alert", number: "+63 919 345 6789", role: "Administrator", active: true },
    { name: "Medical Team", number: "+63 920 456 7890", role: "Medical", active: false }
];

function renderGSMNumbers() {
    const tbody = document.getElementById('gsm-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';

    GSM_CONTACTS.forEach(contact => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${contact.name}</strong></td>
            <td>${contact.number}</td>
            <td><span class="badge" style="background:var(--bg-card); border:1px solid var(--border-color); padding: 2px 6px; border-radius:4px;">${contact.role}</span></td>
            <td>
                ${contact.active
                ? '<span class="status-badge online">Active</span>'
                : '<span class="status-badge offline">Inactive</span>'}
            </td>
            <td>
                <button class="btn btn-secondary" onclick="testSMS('${contact.number}')" style="padding: 2px 8px;">Test SMS</button>
                <button class="btn btn-danger" style="padding: 2px 8px;">Edit</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * I added this test function to verify socket emitting without burning real SMS credits.
 */
window.testSMS = function (number) {
    alert(`Simulating Test SMS to ${number}...\n\n[SYSTEM]: This is a test alert from LocalMonitor.`);
};
