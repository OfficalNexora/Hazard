"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Maximize2, Mic, MicOff, Video, Plus, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDevices } from "@/lib/hooks";
import { ProvisionModal } from "@/components/modals/ProvisionModal";

export default function CamerasPage() {
    const devices = useDevices();
    const cameraDevices = devices.filter(d => d.device_type === 'esp32_cam' || d.device_id.includes('cam'));
    const [isModalOpen, setIsModalOpen] = useState(false);

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
                                    src={`/api/video_feed?id=${cam.device_id}`}
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
                                            <Button size="icon" variant="ghost" className="h-8 w-8 text-white/50 hover:text-white hover:bg-white/10">
                                                <Settings2 className="h-4 w-4" />
                                            </Button>
                                            <Button size="icon" variant="ghost" className="h-8 w-8 text-white/50 hover:text-white hover:bg-white/10">
                                                <Maximize2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                </div>
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
        </div>
    );
}
