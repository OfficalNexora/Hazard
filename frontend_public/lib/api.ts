/**
 * MOD-EVAC-MS - Public Portal API Client
 * Read-only WebSocket connection and REST API integration
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/telemetry';

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

export interface SystemState {
    sensor: SensorData;
    alert: AlertState;
    detections: Detection[];
}

// REST API Functions (Read-only)
export async function fetchSystemStatus(): Promise<SystemState> {
    const res = await fetch(`${API_BASE_URL}/api/status`);
    if (!res.ok) throw new Error('Failed to fetch status');
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
        if (typeof window === 'undefined') return;

        try {
            this.ws = new WebSocket(WS_URL);

            this.ws.onopen = () => {
                this.connected = true;
                this.reconnectAttempts = 0;
                this.emit('connect', {});
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) { }
            };

            this.ws.onclose = () => {
                this.connected = false;
                this.emit('disconnect', {});
                this.scheduleReconnect();
            };
        } catch (e) {
            this.scheduleReconnect();
        }
    }

    private scheduleReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
        setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delay);
    }

    private handleMessage(data: { type: string; data?: unknown }): void {
        const { type } = data;
        switch (type) {
            case 'init': this.emit('init', data.data); break;
            case 'sensor_update': this.emit('sensor', data.data); break;
            case 'detection': this.emit('detection', data.data); break;
            case 'alert_change': this.emit('alert', data.data); break;
        }
    }

    on(event: string, callback: EventCallback): () => void {
        if (!this.listeners.has(event)) this.listeners.set(event, new Set());
        this.listeners.get(event)!.add(callback);
        return () => { this.listeners.get(event)?.delete(callback); };
    }

    private emit(event: string, data: unknown): void {
        this.listeners.get(event)?.forEach((callback) => {
            try { callback(data); } catch (e) { }
        });
    }
}

let wsManager: WebSocketManager | null = null;
export function getWebSocketManager(): WebSocketManager {
    if (!wsManager) wsManager = new WebSocketManager();
    return wsManager;
}
