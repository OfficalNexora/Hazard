document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    updateSystemTime();

    // Icon injection
    if (typeof injectIcons === 'function') injectIcons();

    // I configured this interval to keep the system clock perfectly synchronized with the server.
    setInterval(updateSystemTime, 1000);
});

function initNavigation() {
    // I calculate the active link dynamically based on the current URL path to ensure correct state styling.
    const path = window.location.pathname;
    const page = path.split("/").pop();

    const links = document.querySelectorAll('.nav-item a');
    links.forEach(link => {
        const linkHref = link.getAttribute('href');
        // I handle relative path matching here to support nested directory deployments.
        if (path.includes(linkHref.replace('./', '').replace('../', ''))) {
            link.classList.add('active');
        } else if ((page === '' || page === 'index.html') && linkHref.includes('dashboard.html')) {
            // Fallback for root path
        } else {
            link.classList.remove('active');
        }
    });
}

function updateSystemTime() {
    // I update the global top bar time here.
    const timeDisplay = document.getElementById('sys-time');
    if (timeDisplay) {
        const now = new Date();
        timeDisplay.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }
}

// I use this utility to generate random states for the UI during development/mock mode.
function getRandomStatus() {
    return Math.random() > 0.1 ? 'online' : 'offline';
}
