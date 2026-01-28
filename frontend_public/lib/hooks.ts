'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    SystemState,
    AlertState,
    Detection,
    SensorData,
    getWebSocketManager,
    fetchSystemStatus,
} from './api';

// Hook for public authentication (pairing)
export function usePublicAuth() {
    const [isPaired, setIsPaired] = useState<boolean>(false);
    const [pairingCode, setPairingCode] = useState<string | null>(null);

    useEffect(() => {
        const savedCode = localStorage.getItem('nexus_public_code');
        if (savedCode) {
            setPairingCode(savedCode);
            setIsPaired(true);
        }
    }, []);

    const pair = useCallback(async (code: string) => {
        try {
            const res = await fetch(`http://localhost:8000/api/verify_code?code=${code}`, {
                method: 'POST'
            });
            if (res.ok) {
                localStorage.setItem('nexus_public_code', code);
                setPairingCode(code);
                setIsPaired(true);
                return true;
            }
        } catch (e) {
            console.error('Pairing failed:', e);
        }
        return false;
    }, []);

    const unpair = useCallback(() => {
        localStorage.removeItem('nexus_public_code');
        setPairingCode(null);
        setIsPaired(false);
    }, []);

    return { isPaired, pairingCode, pair, unpair };
}

// Hook for Public Real-time State
export function usePublicState() {
    const [state, setState] = useState<SystemState | null>(null);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const ws = getWebSocketManager();

        const unsubInit = ws.on('init', (data) => {
            setState(data as SystemState);
        });

        const unsubSensor = ws.on('sensor', (data) => {
            setState(prev => prev ? { ...prev, sensor: data as SensorData } : null);
        });

        const unsubAlert = ws.on('alert', (data) => {
            setState(prev => prev ? { ...prev, alert: data as AlertState } : null);
        });

        const unsubDetection = ws.on('detection', (data) => {
            setState(prev => {
                if (!prev) return null;
                const updatedDetections = [data as Detection, ...prev.detections].slice(0, 50);
                return { ...prev, detections: updatedDetections };
            });
        });

        const unsubConnect = ws.on('connect', () => setConnected(true));
        const unsubDisconnect = ws.on('disconnect', () => setConnected(false));

        ws.connect();

        return () => {
            unsubInit();
            unsubSensor();
            unsubAlert();
            unsubDetection();
            unsubConnect();
            unsubDisconnect();
        };
    }, []);

    return { state, connected };
}
