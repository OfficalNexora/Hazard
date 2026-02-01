document.addEventListener('DOMContentLoaded', () => {
    loadContacts();

    const addBtn = document.getElementById('add-contact-btn');
    const modal = document.getElementById('add-modal');
    const saveBtn = document.getElementById('save-contact-btn');

    if (addBtn) {
        addBtn.addEventListener('click', () => {
            modal.style.display = 'block';
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const contact = {
                name: document.getElementById('new-name').value,
                number: document.getElementById('new-number').value,
                mode: document.getElementById('new-mode').value,
                category: document.getElementById('new-category').value,
                message: document.getElementById('new-message').value
            };

            if (!contact.name || !contact.number) {
                alert('Please fill in Name and Number');
                return;
            }

            try {
                await API.addGsmContact(contact);
                modal.style.display = 'none';
                resetForm();
                loadContacts();
            } catch (e) {
                alert('Failed to save contact');
            }
        });
    }
});

async function loadContacts() {
    const list = document.getElementById('contact-list');
    if (!list) return;

    try {
        const data = await API.getGsmContacts();
        list.innerHTML = '';

        // Combine SMS and Call contacts for the table view
        const allContacts = [
            ...(data.sms || []).map(c => ({ ...c, mode: 'sms' })),
            ...(data.call || []).map(c => ({ ...c, mode: 'call' }))
        ];

        if (allContacts.length === 0) {
            list.innerHTML = '<tr><td colspan="5" class="text-muted" style="text-align:center; padding: 2rem;">No contacts registered</td></tr>';
            return;
        }

        allContacts.forEach(contact => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 600;">${contact.name}</div>
                </td>
                <td style="font-family: monospace;">${contact.number}</td>
                <td>
                    <span class="category-badge" style="color: ${contact.mode === 'sms' ? '#3b82f6' : '#f59e0b'}">
                        ${contact.mode.toUpperCase()}
                    </span>
                </td>
                <td>
                    <span class="category-badge">
                        ${contact.category || 'general'}
                    </span>
                </td>
                <td style="text-align: right;">
                    <button class="btn-icon" onclick="removeContact('${contact.number}')">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                    </button>
                </td>
            `;
            list.appendChild(tr);
        });
    } catch (e) {
        console.error('Failed to load contacts', e);
    }
}

async function removeContact(number) {
    if (!confirm(`Remove contact ${number}?`)) return;

    try {
        await API.deleteGsmContact(number);
        loadContacts();
    } catch (e) {
        alert('Failed to delete contact');
    }
}

function resetForm() {
    document.getElementById('new-name').value = '';
    document.getElementById('new-number').value = '';
    document.getElementById('new-message').value = '';
}
