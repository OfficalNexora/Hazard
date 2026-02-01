/**
 * MOD-EVAC-MS - API Client Hooks for Next.js
 * WebSocket connection and REST API integration
 */

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/telemetry';

// Types
export interface SensorData {
    raining: number;
    fire: boolean;
    earthquake: { x: number; y: number; z: number };
    accel: { x: number; y: number; z: number };
    timestamp: number;
}

export interface Detection {
    class: string;
    confidence: number;
    bbox: number[];
    frame_id: number;
    timestamp?: number;
}

export interface AlertState {
    state: string;
    value: number;
    reason?: string;
}

export interface DeviceStatus {
    device_id: string;
    device_type: string;
    type?: string;     // UI helper (alias for device_type)
    connected: boolean;
    last_seen: number;
    port: string;
    status?: string;   // UI helper (e.g., 'READY', 'ALARM')
}

export interface SystemState {
    sensor: SensorData;
    alert: AlertState;
    devices: DeviceStatus[];
    detections: Detection[];
}

// REST API Functions
export async function fetchSystemStatus(): Promise<SystemState> {
    const res = await fetch(`${API_BASE_URL}/api/status`);
    if (!res.ok) throw new Error('Failed to fetch status');
    return res.json();
}

export async function fetchSensorData(): Promise<SensorData> {
    const res = await fetch(`${API_BASE_URL}/api/sensor`);
    if (!res.ok) throw new Error('Failed to fetch sensor data');
    return res.json();
}

export async function fetchDevices(): Promise<{ devices: DeviceStatus[] }> {
    const res = await fetch(`${API_BASE_URL}/api/devices`);
    if (!res.ok) throw new Error('Failed to fetch devices');
    return res.json();
}

export async function fetchDetections(limit: number = 20): Promise<{ detections: Detection[] }> {
    const res = await fetch(`${API_BASE_URL}/api/detections?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch detections');
    return res.json();
}

export async function fetchAlertState(): Promise<AlertState> {
    const res = await fetch(`${API_BASE_URL}/api/alert`);
    if (!res.ok) throw new Error('Failed to fetch alert');
    return res.json();
}

export async function setAlert(alert: number, reason: string = 'Manual'): Promise<AlertState> {
    const res = await fetch(`${API_BASE_URL}/api/alert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert, reason }),
    });
    if (!res.ok) throw new Error('Failed to set alert');
    return res.json();
}

export async function triggerEvacuation(exitZone: number = 3): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/evacuate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exit_zone: exitZone }),
    });
    if (!res.ok) throw new Error('Failed to trigger evacuation');
    return res.json();
}

export async function setSafeMode(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/safe`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to set safe mode');
    return res.json();
}

export async function fetchHistory(limit: number = 50): Promise<{ history: Detection[] }> {
    const res = await fetch(`${API_BASE_URL}/api/history?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
}

export async function fetchSettings(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/settings`);
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
}

export async function updateSettings(config: any): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
}

export async function fetchAccessCode(): Promise<{ code: string }> {
    const res = await fetch(`${API_BASE_URL}/api/access_code`);
    if (!res.ok) throw new Error('Failed to fetch access code');
    return res.json();
}

export async function verifyCode(code: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/verify_code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
    });
    if (!res.ok) throw new Error('Invalid access code');
    return res.json();
}

export async function addGsmContact(mode: 'sms' | 'call', number: string, name: string, message?: string, category: string = 'general'): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/gsm/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, number, name, message: message || '', category }),
    });
    if (!res.ok) throw new Error('Failed to add contact');
    return res.json();
}

export async function deleteGsmContact(number: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/gsm/contacts/${encodeURIComponent(number)}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete contact');
    return res.json();
}

export async function fetchGsmContacts(): Promise<{ sms: any[], call: any[] }> {
    const res = await fetch(`${API_BASE_URL}/api/gsm/contacts`);
    if (!res.ok) throw new Error('Failed to fetch contacts');
    return res.json();
}

export async function triggerManualAction(actionType: string, details: string = ''): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/manual/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_type: actionType, details }),
    });
    if (!res.ok) throw new Error('Failed to trigger action');
    return res.json();
}

export async function classifyWorker(deviceId: string, classification: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/cluster/classify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId, classification }),
    });
    if (!res.ok) throw new Error('Failed to classify worker');
    return res.json();
}

export async function registerCamera(deviceId: string, ip: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/api/cameras/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId, ip }),
    });
    if (!res.ok) throw new Error('Failed to register camera');
    return res.json();
}

/**
 * Direct handshake with ESP32-CAM in AP mode
 * laptop must be connected to camera's WiFi
 */
export async function provisionCamera(config: { ssid: string, password: string, server_ip: string }): Promise<{ status: string }> {
    const res = await fetch(`http://192.168.4.1/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to provision camera. Are you connected to its WiFi?');
    return res.json();
}

// WebSocket Manager
export type EventCallback = (data: unknown) => void;

class WebSocketManager {
    private ws: WebSocket | null = null;
    private listeners: Map<string, Set<EventCallback>> = new Map();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 10;
    private reconnectDelay = 1000;
    private connected = false;

    connect(): void {
        if (typeof window === 'undefined') return; // SSR guard

        try {
            this.ws = new WebSocket(WS_URL);

            this.ws.onopen = () => {
                console.log('[WS] Connected');
                this.connected = true;
                this.reconnectAttempts = 0;
                this.emit('connect', {});
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('[WS] Parse error:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('[WS] Disconnected');
                this.connected = false;
                this.emit('disconnect', {});
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('[WS] Error:', error);
                this.emit('error', { message: 'WebSocket error' });
            };
        } catch (e) {
            console.error('[WS] Connection failed:', e);
            this.scheduleReconnect();
        }
    }

    private scheduleReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WS] Max reconnect attempts reached');
            return;
        }

        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
        console.log(`[WS] Reconnecting in ${delay}ms...`);

        setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delay);
    }

    private handleMessage(data: { type: string; data?: unknown }): void {
        const { type } = data;

        switch (type) {
            case 'init':
                this.emit('init', data.data);
                break;
            case 'sensor_update':
                this.emit('sensor', data.data);
                break;
            case 'detection':
                this.emit('detection', data.data);
                break;
            case 'alert_change':
                this.emit('alert', data.data);
                break;
            case 'device_update':
                this.emit('device', data.data);
                break;
            case 'keepalive':
            case 'pong':
                break;
            default:
                console.log('[WS] Unknown message type:', type);
        }
    }

    on(event: string, callback: EventCallback): () => void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event)!.add(callback);

        // Return unsubscribe function
        return () => {
            this.listeners.get(event)?.delete(callback);
        };
    }

    private emit(event: string, data: unknown): void {
        this.listeners.get(event)?.forEach((callback) => {
            try {
                callback(data);
            } catch (e) {
                console.error(`[WS] Listener error (${event}):`, e);
            }
        });
    }

    send(data: object): void {
        if (this.ws && this.connected) {
            this.ws.send(JSON.stringify(data));
        }
    }

    isConnected(): boolean {
        return this.connected;
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Singleton instance
let wsManager: WebSocketManager | null = null;

export function getWebSocketManager(): WebSocketManager {
    if (!wsManager) {
        wsManager = new WebSocketManager();
    }
    return wsManager;
}

export function connectWebSocket(): void {
    getWebSocketManager().connect();
}

export function disconnectWebSocket(): void {
    getWebSocketManager().disconnect();
}
