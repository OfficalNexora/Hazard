"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Wifi, Server, Camera, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { provisionCamera, registerCamera } from "@/lib/api";

interface ProvisionModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function ProvisionModal({ open, onOpenChange, onSuccess }: ProvisionModalProps) {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [config, setConfig] = useState({
        ssid: "",
        password: "",
        server_ip: "192.168.1.100", // Default or current IP
        name: "Nexora Cam " + Math.floor(Math.random() * 1000)
    });

    const handleProvision = async () => {
        setLoading(true);
        setError(null);
        try {
            // 1. Handshake with ESP32-CAM (Direct to 192.168.4.1)
            await provisionCamera({
                ssid: config.ssid,
                password: config.password,
                server_ip: config.server_ip
            });

            setStep(2); // Success step

            // 2. Register on Backend (Wait a bit for camera to reboot and connect)
            // In a real scenario, we might wait for discovery, but here we register immediately
            await registerCamera(config.name.replace(/\s+/g, '_').toLowerCase(), "unknown");

        } catch (e: any) {
            setError(e.message || "Provisioning failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px] bg-zinc-950 border-white/5">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Camera className="w-5 h-5 text-blue-500" />
                        Provision WiFi Camera
                    </DialogTitle>
                    <DialogDescription>
                        Follow the steps to connect a new ESP32-CAM to the system.
                    </DialogDescription>
                </DialogHeader>

                {step === 1 ? (
                    <div className="grid gap-4 py-4">
                        <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-xs text-blue-400">
                            <strong>1. First Step:</strong> Connect your computer to the WiFi network: <strong>NEXORA_CAM_XXXX</strong>.
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="ssid">WiFi Network Name (SSID)</Label>
                            <Input
                                id="ssid"
                                value={config.ssid}
                                onChange={(e) => setConfig({ ...config, ssid: e.target.value })}
                                placeholder="Evacuation_Net"
                                className="bg-white/5 border-white/10"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="pass">WiFi Password</Label>
                            <Input
                                id="pass"
                                type="password"
                                value={config.password}
                                onChange={(e) => setConfig({ ...config, password: e.target.value })}
                                placeholder="••••••••"
                                className="bg-white/5 border-white/10"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="server">Server/Laptop IP Address</Label>
                            <Input
                                id="server"
                                value={config.server_ip}
                                onChange={(e) => setConfig({ ...config, server_ip: e.target.value })}
                                placeholder="192.168.x.x"
                                className="bg-white/5 border-white/10"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="name">Camera Nickname</Label>
                            <Input
                                id="name"
                                value={config.name}
                                onChange={(e) => setConfig({ ...config, name: e.target.value })}
                                placeholder="Entrance Gate"
                                className="bg-white/5 border-white/10"
                            />
                        </div>

                        {error && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
                        <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center">
                            <CheckCircle2 className="w-8 h-8 text-green-500" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg">Provisioning Started</h3>
                            <p className="text-sm text-zinc-400">
                                The camera is rebooting to connect to <strong>{config.ssid}</strong>.
                                It should appear in the feed in a moment.
                            </p>
                        </div>
                        <div className="pt-4 text-xs text-zinc-500">
                            Don't forget to connect your laptop back to <strong>{config.ssid}</strong>.
                        </div>
                    </div>
                )}

                <DialogFooter>
                    {step === 1 ? (
                        <Button
                            onClick={handleProvision}
                            disabled={loading || !config.ssid || !config.server_ip}
                            className="w-full bg-blue-600 hover:bg-blue-700"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Wifi className="w-4 h-4 mr-2" />}
                            Start Handshake
                        </Button>
                    ) : (
                        <Button
                            onClick={() => { onOpenChange(false); onSuccess(); }}
                            className="w-full"
                        >
                            Done
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
