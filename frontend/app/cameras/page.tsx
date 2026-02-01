"use client";

import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Maximize2, Mic, MicOff, Video, Plus, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDevices } from "@/lib/hooks";
import { ProvisionModal } from "@/components/modals/ProvisionModal";

// API Configuration - must match backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CamerasPage() {
    const devices = useDevices();
    const cameraDevices = devices.filter(d =>
        d.device_type === 'esp32_cam' ||
        d.device_type === 'camera' ||
        d.device_id.includes('cam')
    );
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [talkingCameras, setTalkingCameras] = useState<Set<string>>(new Set());
    const [showControls, setShowControls] = useState<Set<string>>(new Set());

    // Position tracking for draggable controls: { deviceId: { x, y } }
    const [controlPositions, setControlPositions] = useState<Record<string, { x: number, y: number }>>({});
    const [dragOffset, setDragOffset] = useState<{ x: number, y: number } | null>(null);
    const [draggingCam, setDraggingCam] = useState<string | null>(null);

    // PTZ Status tracking
    const [camStatus, setCamStatus] = useState<Record<string, { pan: number, tilt: number, zoom: number }>>({});

    // Throttle lock
    const processingRef = useRef<Set<string>>(new Set());

    // Keyboard handlers
    useEffect(() => {
        const handleKeyDown = async (e: KeyboardEvent) => {
            // Only if a control is visible
            if (showControls.size === 0) return;

            // Just control the first/most recently active one or active hover? 
            // For now, let's control ALL open controls (simple sync) or valid focused one.
            // Better: Control the LAST opened one.
            const targetId = Array.from(showControls).pop();
            if (!targetId) return;
            // Throttle check
            if (processingRef.current.has(targetId)) return;

            const STEP = 0.1;
            let p = 0, t = 0;

            if (e.key === 'ArrowUp') t = STEP;
            else if (e.key === 'ArrowDown') t = -STEP;
            else if (e.key === 'ArrowLeft') p = -STEP;
            else if (e.key === 'ArrowRight') p = STEP;
            else if (e.key === 'PageUp') { /* Todo Zoom In */ }
            else if (e.key === 'PageDown') { /* Todo Zoom Out */ }
            else return;

            e.preventDefault();

            processingRef.current.add(targetId);
            try {
                const { moveCamera } = await import("@/lib/api");
                const res = await moveCamera(targetId, p, t);
                if (res.new_position) {
                    setCamStatus(prev => ({ ...prev, [targetId]: res.new_position }));
                }
            } catch (err) {
                console.error("PTZ Key Error", err);
            } finally {
                processingRef.current.delete(targetId);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [showControls]);

    const handleMouseDown = (e: React.MouseEvent, deviceId: string) => {
        setDraggingCam(deviceId);
        const rect = (e.currentTarget.parentElement as HTMLElement).getBoundingClientRect();
        setDragOffset({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!draggingCam || !dragOffset) return;
        // This relies on the container being relative or fixed. 
        // We'll update the absolute position relative to the CARD.
        // Actually, simplest is to use translate transforms or standard left/top styles.
        // Let's store offset from the default "center bottom" or just raw x/y relative to card top-left.
        // To keep it simple inside the card, we'll just track style changes.

        // Simpler implementation: Just allow modest nudging or use a library.
        // Since we are doing it manually:
        // We need the parent card bounds.
        // This is getting complex for a "simple" drag. 
        // Let's try to just update the `controlPositions` state.
    };

    // We will use a simpler global mouse up listener for drag end
    useEffect(() => {
        const handleGlobalMouseUp = () => {
            setDraggingCam(null);
            setDragOffset(null);
        };
        const handleGlobalMouseMove = (e: MouseEvent) => {
            if (draggingCam && dragOffset) {
                // Calculate new position. We need a way to reference the card. 
                // Without complex refs, we can just use fixed/absolute coordinates relative to screen 
                // or just delta updates. 
                // Let's assume we update a generic delta from the initial "center bottom" position?
                // No, standard X/Y absolute within the card is best.

                // NOTE: Implementing full drag correctly in this one-shot tool is risky without context.
                // I will implement the draggable HEADER in the JSX and use a simple position offset state.

                setControlPositions(prev => ({
                    ...prev,
                    [draggingCam]: {
                        x: prev[draggingCam]?.x || 0 + e.movementX, // Delta usage is easier
                        y: prev[draggingCam]?.y || 0 + e.movementY
                    }
                }));
            }
        };
        window.addEventListener('mouseup', handleGlobalMouseUp);
        window.addEventListener('mousemove', handleGlobalMouseMove);
        return () => {
            window.removeEventListener('mouseup', handleGlobalMouseUp);
            window.removeEventListener('mousemove', handleGlobalMouseMove);
        }
    }, [draggingCam, dragOffset]);

    const toggleTalk = (deviceId: string) => {
        const newTalking = new Set(talkingCameras);
        if (newTalking.has(deviceId)) {
            newTalking.delete(deviceId);
        } else {
            newTalking.add(deviceId);
        }
        setTalkingCameras(newTalking);
    };

    const toggleControls = (deviceId: string) => {
        const newControls = new Set(showControls);
        if (newControls.has(deviceId)) {
            newControls.delete(deviceId);
        } else {
            newControls.add(deviceId);
        }
        setShowControls(newControls);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground">Surveillance Feeds</h1>
                    <p className="text-muted-foreground">Real-time CCTV monitoring and device provisioning.</p>
                </div>
                <div className="flex gap-2">
                    <Button
                        onClick={() => setIsModalOpen(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20"
                    >
                        <Plus className="mr-2 h-4 w-4" />
                        Provision Camera
                    </Button>
                </div>
            </div>

            {cameraDevices.length === 0 ? (
                <Card className="p-12 border-dashed bg-black/20 border-white/5 flex flex-col items-center justify-center text-center space-y-4">
                    <div className="w-16 h-16 rounded-full bg-zinc-900 flex items-center justify-center">
                        <Video className="w-8 h-8 text-zinc-500" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold">No Cameras Found</h3>
                        <p className="text-sm text-muted-foreground max-w-sm">
                            No active camera streams detected on the network. Use the provisioning tool to add your first ESP32-CAM.
                        </p>
                    </div>
                    <Button variant="outline" onClick={() => setIsModalOpen(true)}>
                        Deploy First Camera
                    </Button>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {cameraDevices.map((cam) => (
                        <Card key={cam.device_id} className="overflow-hidden bg-black/40 border-slate-800 group border-white/5">
                            <div className="relative aspect-video bg-zinc-900">
                                {/* Real Video Stream Relay */}
                                <img
                                    src={`${API_BASE_URL}/api/video_feed?id=${cam.device_id}`}
                                    className="w-full h-full object-cover"
                                    alt={cam.device_id}
                                    onError={(e) => {
                                        const target = e.target as HTMLImageElement;
                                        target.style.display = 'none';
                                        target.nextElementSibling?.classList.remove('hidden');
                                    }}
                                />

                                {/* Placeholder if stream fails */}
                                <div className="absolute inset-0 hidden flex items-center justify-center text-zinc-700 bg-zinc-900">
                                    <div className="flex flex-col items-center gap-2">
                                        <Video className="h-12 w-12 opacity-20" />
                                        <span className="text-xs font-mono uppercase">Loss of Signal</span>
                                    </div>
                                </div>

                                {/* Overlays */}
                                <div className="absolute top-4 left-4 flex gap-2">
                                    <Badge variant={cam.connected ? 'default' : 'secondary'} className={cam.connected ? 'bg-green-500/80 hover:bg-green-500 text-white' : ''}>
                                        {cam.connected ? 'LIVE' : 'OFFLINE'}
                                    </Badge>
                                </div>

                                <div className="absolute top-4 right-4 text-[10px] font-mono text-white/50 bg-black/50 px-2 py-1 rounded backdrop-blur-sm">
                                    {cam.last_seen ? new Date(cam.last_seen * 1000).toLocaleTimeString() : '00:00:00'}
                                </div>

                                <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 to-transparent translate-y-2 group-hover:translate-y-0 transition-transform duration-300">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                                                {cam.device_id.replace(/_/g, ' ')}
                                            </h3>
                                            <p className="text-[10px] text-zinc-400 font-mono">{cam.status || 'READY'}</p>
                                        </div>
                                        <div className="flex gap-1">
                                            <Button
                                                size="icon"
                                                variant={showControls.has(cam.device_id) ? "secondary" : "ghost"}
                                                className={`h-8 w-8 text-white/50 hover:text-white hover:bg-white/10 ${showControls.has(cam.device_id) ? "bg-white/20 text-white" : ""}`}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    toggleControls(cam.device_id);
                                                }}
                                            >
                                                <Settings2 className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                size="icon"
                                                variant={talkingCameras.has(cam.device_id) ? "destructive" : "ghost"}
                                                className={`h-8 w-8 rounded-full ${talkingCameras.has(cam.device_id) ? "animate-pulse" : "text-white/50 hover:text-white hover:bg-white/10"}`}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    toggleTalk(cam.device_id);
                                                }}
                                            >
                                                {talkingCameras.has(cam.device_id) ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
                                            </Button>
                                            <Button size="icon" variant="secondary" className="h-6 w-6 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Maximize2 className="h-3 w-3" />
                                            </Button>

                                            {/* Delete Button */}
                                            <Button
                                                size="icon"
                                                variant="destructive"
                                                className="h-6 w-6 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                                                onClick={async (e) => {
                                                    e.stopPropagation();
                                                    if (!confirm(`Delete camera ${cam.device_id}?`)) return;

                                                    try {
                                                        const { deleteCamera } = await import("@/lib/api");
                                                        await deleteCamera(cam.device_id);
                                                        // Refresh automatically handled by hook polling
                                                    } catch (err) {
                                                        alert("Failed to delete camera");
                                                    }
                                                }}
                                            >
                                                <Plus className="h-3 w-3 rotate-45" /> {/* X icon */}
                                            </Button>
                                        </div>
                                    </div>
                                </div>


                                {/* PTZ Control Pad (Draggable & Key-enabled) */}
                                {showControls.has(cam.device_id) && (
                                    <div
                                        className="absolute z-50 w-48 shadow-2xl transition-opacity duration-200"
                                        style={{
                                            left: `calc(50% + ${controlPositions[cam.device_id]?.x || 0}px)`,
                                            bottom: `calc(4rem - ${controlPositions[cam.device_id]?.y || 0}px)`,
                                            transform: 'translateX(-50%)',
                                        }}
                                    >
                                        <div className="bg-black/90 backdrop-blur-md rounded-xl border border-white/20 overflow-hidden">
                                            {/* Drag Handle */}
                                            <div
                                                className="h-6 bg-white/10 w-full cursor-move flex items-center justify-center"
                                                onMouseDown={(e) => {
                                                    e.stopPropagation();
                                                    handleMouseDown(e, cam.device_id);
                                                }}
                                            >
                                                <div className="w-8 h-1 bg-white/30 rounded-full" />
                                            </div>

                                            <div className="p-3">
                                                {/* Status Indicator (if available) */}
                                                {camStatus[cam.device_id] && (
                                                    <div className="text-[10px] text-center mb-2 font-mono text-cyan-400">
                                                        X:{camStatus[cam.device_id].pan.toFixed(2)} Y:{camStatus[cam.device_id].tilt.toFixed(2)}
                                                    </div>
                                                )}

                                                <div className="grid grid-cols-3 gap-1 mb-2">
                                                    <div></div>
                                                    <Button
                                                        size="icon"
                                                        variant={
                                                            (camStatus[cam.device_id]?.tilt ?? 0) >= 0.9
                                                                ? "destructive" : "secondary"
                                                        }
                                                        className={`h-10 w-10 rounded-lg transition-colors ${(camStatus[cam.device_id]?.tilt ?? 0) >= 0.9
                                                                ? "opacity-50 cursor-not-allowed"
                                                                : "hover:bg-cyan-500/20 hover:text-cyan-400"
                                                            }`}
                                                        onClick={async (e) => {
                                                            e.stopPropagation();
                                                            if ((camStatus[cam.device_id]?.tilt ?? 0) >= 0.95) return; // Hard limit check
                                                            if (processingRef.current.has(cam.device_id)) return;
                                                            processingRef.current.add(cam.device_id);
                                                            try {
                                                                const { moveCamera } = await import("@/lib/api");
                                                                const res = await moveCamera(cam.device_id, 0, 0.1);
                                                                if (res.new_position) setCamStatus(prev => ({ ...prev, [cam.device_id]: res.new_position }));
                                                            } finally {
                                                                processingRef.current.delete(cam.device_id);
                                                            }
                                                        }}
                                                    >
                                                        ↑
                                                    </Button>
                                                    <div></div>
                                                    <Button
                                                        size="icon"
                                                        variant="secondary"
                                                        className="h-10 w-10 rounded-lg hover:bg-cyan-500/20 hover:text-cyan-400"
                                                        onClick={async (e) => {
                                                            e.stopPropagation();
                                                            if (processingRef.current.has(cam.device_id)) return;
                                                            processingRef.current.add(cam.device_id);
                                                            try {
                                                                const { moveCamera } = await import("@/lib/api");
                                                                const res = await moveCamera(cam.device_id, -0.1, 0); // Step
                                                                if (res.new_position) setCamStatus(prev => ({ ...prev, [cam.device_id]: res.new_position }));
                                                            } finally {
                                                                processingRef.current.delete(cam.device_id);
                                                            }
                                                        }}
                                                    >
                                                        ←
                                                    </Button>
                                                    <Button
                                                        size="icon"
                                                        variant={
                                                            (camStatus[cam.device_id]?.tilt ?? 0) <= -0.9
                                                                ? "destructive" : "secondary"
                                                        }
                                                        className={`h-10 w-10 rounded-lg transition-colors ${(camStatus[cam.device_id]?.tilt ?? 0) <= -0.9
                                                                ? "opacity-50 cursor-not-allowed"
                                                                : "hover:bg-cyan-500/20 hover:text-cyan-400"
                                                            }`}
                                                        onClick={async (e) => {
                                                            e.stopPropagation();
                                                            if ((camStatus[cam.device_id]?.tilt ?? 0) <= -0.95) return;
                                                            if (processingRef.current.has(cam.device_id)) return;
                                                            processingRef.current.add(cam.device_id);
                                                            try {
                                                                const { moveCamera } = await import("@/lib/api");
                                                                const res = await moveCamera(cam.device_id, 0, -0.1);
                                                                if (res.new_position) setCamStatus(prev => ({ ...prev, [cam.device_id]: res.new_position }));
                                                            } finally {
                                                                processingRef.current.delete(cam.device_id);
                                                            }
                                                        }}
                                                    >
                                                        ↓
                                                    </Button>
                                                    <Button
                                                        size="icon"
                                                        variant="secondary"
                                                        className="h-10 w-10 rounded-lg hover:bg-cyan-500/20 hover:text-cyan-400"
                                                        onClick={async (e) => {
                                                            e.stopPropagation();
                                                            if (processingRef.current.has(cam.device_id)) return;
                                                            processingRef.current.add(cam.device_id);
                                                            try {
                                                                const { moveCamera } = await import("@/lib/api");
                                                                const res = await moveCamera(cam.device_id, 0.1, 0); // Step
                                                                if (res.new_position) setCamStatus(prev => ({ ...prev, [cam.device_id]: res.new_position }));
                                                            } finally {
                                                                processingRef.current.delete(cam.device_id);
                                                            }
                                                        }}
                                                    >
                                                        →
                                                    </Button>
                                                </div>
                                                <div className="text-[10px] text-zinc-500 text-center">
                                                    Use Arrow Keys
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            <ProvisionModal
                open={isModalOpen}
                onOpenChange={setIsModalOpen}
                onSuccess={() => {
                    // Logic to refresh or wait
                }}
            />
        </div >
    );
}
