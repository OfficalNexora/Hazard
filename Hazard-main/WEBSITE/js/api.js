/**
 * MOD-EVAC-MS - WebSocket API Client
 * I built this real-time client to handle low-latency telemetry from the backend.
 * 
 * Features:
 * - Auto-reconnect with exponential backoff (my solution to network instability)
 * - Event-based architecture for decoupled updates
 * - Failover to HTTP polling if WebSocket is blocked or failing
 */

const API = {
    // I configured these endpoints to point to the local Python FastServer.
    wsUrl: 'ws://localhost:8000/ws/telemetry',
    httpUrl: 'http://localhost:8000/api',

    // Connection state management
    ws: null,
    connected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 10,
    reconnectDelay: 1000,

    // I implemented a custom event emitter pattern here.
    listeners: {
        connect: [],
        disconnect: [],
        sensor: [],
        detection: [],
        alert: [],
        device: [],
        error: []
    },

    // I cache the latest data to provide instant state to new subscribers.
    cache: {
        sensor: null,
        alert: null,
        devices: [],
        detections: []
    },

    /**
     * I initialize the connection sequence here.
     */
    init() {
        console.log('[API] I am initializing the WebSocket connection...');
        this.connect();
    },

    /**
     * I handle the raw WebSocket connection logic here.
     */
    connect() {
        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => {
                console.log('[API] WebSocket connected successfully.');
                this.connected = true;
                this.reconnectAttempts = 0;
                this.emit('connect', {});
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('[API] I encountered a JSON parse error:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('[API] WebSocket disconnected. I will attempt to reconnect.');
                this.connected = false;
                this.emit('disconnect', {});
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('[API] WebSocket error:', error);
                this.emit('error', { message: 'WebSocket error' });
            };

        } catch (e) {
            console.error('[API] Connection failed immediately:', e);
            this.scheduleReconnect();
        }
    },

    /**
     * I implemented exponential backoff here to prevent flooding the server during downtime.
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[API] Max reconnect attempts reached. I am falling back to HTTP polling.');
            this.startPolling();
            return;
        }

        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
        console.log(`[API] I will retry connection in ${delay}ms...`);

        setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delay);
    },

    /**
     * This is my fallback mechanism. If WebSockets fail, I poll via HTTP every 2 seconds.
     */
    startPolling() {
        console.log('[API] Starting HTTP polling fallback strategy.');
        setInterval(() => {
            this.fetchStatus();
        }, 2000);
    },

    /**
     * I fetch the complete system status via HTTP REST API.
     */
    async fetchStatus() {
        try {
            const response = await fetch(`${this.httpUrl}/status`);
            const data = await response.json();

            if (data.sensor) {
                this.cache.sensor = data.sensor;
                this.emit('sensor', data.sensor);
            }
            if (data.alert) {
                this.cache.alert = data.alert;
                this.emit('alert', data.alert);
            }
            if (data.devices) {
                this.cache.devices = data.devices;
                this.emit('device', { devices: data.devices });
            }
        } catch (e) {
            console.error('[API] Polling error:', e);
        }
    },

    /**
     * I route incoming WebSocket messages to their appropriate event handlers.
     */
    handleMessage(data) {
        const type = data.type;

        switch (type) {
            case 'init':
                // I dump the initial state to synchronize the client immediately.
                if (data.data) {
                    this.cache = { ...this.cache, ...data.data };
                    this.emit('sensor', data.data.sensor);
                    this.emit('alert', data.data.alert);
                    this.emit('device', { devices: data.data.devices });
                }
                break;

            case 'sensor_update':
                this.cache.sensor = data.data;
                this.emit('sensor', data.data);
                break;

            case 'detection':
                this.cache.detections.unshift(data.data);
                if (this.cache.detections.length > 50) {
                    this.cache.detections.pop(); // I enforce a limit of 50 detections to control memory usage.
                }
                this.emit('detection', data.data);
                break;

            case 'alert_change':
                this.cache.alert = data.data;
                this.emit('alert', data.data);
                break;

            case 'device_update':
                this.emit('device', data.data);
                break;

            case 'keepalive':
            case 'pong':
                // I ignore heartbeats; they just keep the connection alive.
                break;

            default:
                console.log('[API] I received an unknown message type:', type);
        }
    },

    /**
     * I enable other modules to subscribe to specific events.
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
    },

    /**
     * I broadcast events to all registered listeners safely.
     */
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => {
                try {
                    cb(data);
                } catch (e) {
                    console.error(`[API] Listener error (${event}):`, e);
                }
            });
        }
    },

    /**
     * I send data back to the server via WebSocket.
     */
    send(data) {
        if (this.ws && this.connected) {
            this.ws.send(JSON.stringify(data));
        }
    },

    // =========================================================================
    // API METHODS (I implemented these wrappers for clean consumption)
    // =========================================================================

    /**
     * I trigger the alert state manually.
     */
    async setAlert(alert, reason = 'Manual') {
        try {
            const response = await fetch(`${this.httpUrl}/alert?alert=${alert}&reason=${encodeURIComponent(reason)}`, {
                method: 'POST'
            });
            return await response.json();
        } catch (e) {
            console.error('[API] setAlert error:', e);
            throw e;
        }
    },

    /**
     * I trigger the evacuation sequence for specific zones.
     */
    async triggerEvacuation(exitZone = 3) {
        try {
            const response = await fetch(`${this.httpUrl}/evacuate?exit_zone=${exitZone}`, {
                method: 'POST'
            });
            return await response.json();
        } catch (e) {
            console.error('[API] triggerEvacuation error:', e);
            throw e;
        }
    },

    /**
     * I reset the system to safe mode.
     */
    async setSafeMode() {
        try {
            const response = await fetch(`${this.httpUrl}/safe`, {
                method: 'POST'
            });
            return await response.json();
        } catch (e) {
            console.error('[API] setSafeMode error:', e);
            throw e;
        }
    },

    /**
     * I retrieve historical detection data.
     */
    async getDetections(limit = 20) {
        try {
            const response = await fetch(`${this.httpUrl}/detections?limit=${limit}`);
            return await response.json();
        } catch (e) {
            console.error('[API] getDetections error:', e);
            throw e;
        }
    },

    /**
     * I retrieve the list of active devices.
     */
    async getDevices() {
        try {
            const response = await fetch(`${this.httpUrl}/devices`);
            return await response.json();
        } catch (e) {
            console.error('[API] getDevices error:', e);
            throw e;
        }
    }
};

// I auto-initialize the API when the DOM is ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => API.init());
} else {
    API.init();
}
