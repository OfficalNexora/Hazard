'use client';

/**
 * MOD-EVAC-MS - Real-time Data Hooks
 * React hooks for WebSocket and API data
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    SensorData,
    Detection,
    AlertState,
    DeviceStatus,
    SystemState,
    getWebSocketManager,
    fetchSystemStatus,
    setAlert as apiSetAlert,
    triggerEvacuation as apiTriggerEvacuation,
    setSafeMode as apiSetSafeMode,
    fetchHistory,
    fetchSettings,
    updateSettings as apiUpdateSettings,
    fetchAccessCode,
} from './api';

// Hook for real-time sensor data
export function useSensorData() {
    const [data, setData] = useState<SensorData | null>(null);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const ws = getWebSocketManager();

        const unsubSensor = ws.on('sensor', (sensorData) => {
            setData(sensorData as SensorData);
        });

        const unsubInit = ws.on('init', (state) => {
            const s = state as SystemState;
            if (s?.sensor) setData(s.sensor);
        });

        const unsubConnect = ws.on('connect', () => setConnected(true));
        const unsubDisconnect = ws.on('disconnect', () => setConnected(false));

        ws.connect();

        return () => {
            unsubSensor();
            unsubInit();
            unsubConnect();
            unsubDisconnect();
        };
    }, []);

    return { data, connected };
}

// Hook for alert state
export function useAlertState() {
    const [alert, setAlertState] = useState<AlertState>({ state: 'SAFE', value: 0 });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const ws = getWebSocketManager();

        const unsubAlert = ws.on('alert', (alertData) => {
            setAlertState(alertData as AlertState);
        });

        const unsubInit = ws.on('init', (state) => {
            const s = state as SystemState;
            if (s?.alert) setAlertState(s.alert);
        });

        ws.connect();

        return () => {
            unsubAlert();
            unsubInit();
        };
    }, []);

    const setAlert = useCallback(async (value: number, reason?: string) => {
        setLoading(true);
        try {
            const result = await apiSetAlert(value, reason);
            setAlertState(result);
        } finally {
            setLoading(false);
        }
    }, []);

    const triggerEvacuation = useCallback(async (exitZone?: number) => {
        setLoading(true);
        try {
            await apiTriggerEvacuation(exitZone);
            setAlertState({ state: 'EVACUATE', value: 4 });
        } finally {
            setLoading(false);
        }
    }, []);

    const setSafeMode = useCallback(async () => {
        setLoading(true);
        try {
            await apiSetSafeMode();
            setAlertState({ state: 'SAFE', value: 0 });
        } finally {
            setLoading(false);
        }
    }, []);

    return { alert, setAlert, triggerEvacuation, setSafeMode, loading };
}

// Hook for detections stream
export function useDetections(maxItems: number = 50) {
    const [detections, setDetections] = useState<Detection[]>([]);

    useEffect(() => {
        const ws = getWebSocketManager();

        const unsubDetection = ws.on('detection', (detection) => {
            setDetections((prev) => {
                const updated = [detection as Detection, ...prev];
                return updated.slice(0, maxItems);
            });
        });

        const unsubInit = ws.on('init', (state) => {
            const s = state as SystemState;
            if (s?.detections) setDetections(s.detections.slice(0, maxItems));
        });

        ws.connect();

        return () => {
            unsubDetection();
            unsubInit();
        };
    }, [maxItems]);

    return detections;
}

// Hook for device status
export function useDevices() {
    const [devices, setDevices] = useState<DeviceStatus[]>([]);

    useEffect(() => {
        const ws = getWebSocketManager();

        const unsubDevice = ws.on('device', (deviceData) => {
            const data = deviceData as { device_id: string; connected: boolean };
            setDevices((prev) => {
                const idx = prev.findIndex((d) => d.device_id === data.device_id);
                if (idx >= 0) {
                    const updated = [...prev];
                    updated[idx] = { ...updated[idx], ...data } as DeviceStatus;
                    return updated;
                }
                return [...prev, data as DeviceStatus];
            });
        });

        const unsubInit = ws.on('init', (state) => {
            const s = state as SystemState;
            if (s?.devices) setDevices(s.devices);
        });

        ws.connect();

        return () => {
            unsubDevice();
            unsubInit();
        };
    }, []);

    return devices;
}

// Hook for cluster workers
export function useWorkers() {
    const [workers, setWorkers] = useState<any[]>([]);

    useEffect(() => {
        const refresh = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/workers');
                const data = await res.json();
                setWorkers(data.workers || []);
            } catch (e) {
                console.error('Failed to fetch workers:', e);
            }
        };

        refresh();
        const interval = setInterval(refresh, 5000);
        return () => clearInterval(interval);
    }, []);

    return workers;
}

// Hook for full system state with periodic refresh
export function useSystemState(refreshInterval: number = 5000) {
    const [state, setState] = useState<SystemState | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        try {
            const data = await fetchSystemStatus();
            setState(data);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to fetch status');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();

        // WebSocket updates
        const ws = getWebSocketManager();
        ws.connect();

        const unsubInit = ws.on('init', (data) => {
            setState(data as SystemState);
            setLoading(false);
        });

        // Periodic refresh as fallback
        const interval = setInterval(refresh, refreshInterval);

        return () => {
            unsubInit();
            clearInterval(interval);
        };
    }, [refresh, refreshInterval]);

    return { state, loading, error, refresh };
}

// Hook for historical data
export function useHistory(limit: number = 50) {
    const [history, setHistory] = useState<Detection[]>([]);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const data = await fetchHistory(limit);
            setHistory(data.history);
        } catch (e) {
            console.error('Failed to fetch history:', e);
        } finally {
            setLoading(false);
        }
    }, [limit]);

    useEffect(() => {
        refresh();
    }, [refresh]);

    return { history, loading, refresh };
}

// Hook for system settings
export function useSettings() {
    const [settings, setSettings] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const data = await fetchSettings();
            setSettings(data);
        } catch (e) {
            console.error('Failed to fetch settings:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    const update = useCallback(async (newSettings: any) => {
        setLoading(true);
        try {
            await apiUpdateSettings(newSettings);
            setSettings(newSettings);
            return true;
        } catch (e) {
            console.error('Failed to update settings:', e);
            return false;
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    return { settings, loading, update, refresh };
}

// Hook for public access code
export function useAccessCode() {
    const [code, setCode] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const data = await fetchAccessCode();
            setCode(data.code);
        } catch (e) {
            console.error('Failed to fetch access code:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    return { code, loading, refresh };
}
