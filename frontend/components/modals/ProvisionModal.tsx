"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Wifi,
    Server,
    Camera,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Search,
    Network
} from "lucide-react";
import { provisionCamera, registerCamera, registerTapoCamera, discoverCameras, discoverRtspCameras } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

interface ProvisionModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function ProvisionModal({ open, onOpenChange, onSuccess }: ProvisionModalProps) {
    const [activeTab, setActiveTab] = useState("manual");
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [scanning, setScanning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [foundCameras, setFoundCameras] = useState<{ ip: string, model: string }[]>([]);
    const [foundRtsp, setFoundRtsp] = useState<{ ip: string, ports: number[], type: string, suggested_port: number }[]>([]);
    const [scanningRtsp, setScanningRtsp] = useState(false);

    // Config for SoftAP Provisioning
    const [config, setConfig] = useState({
        ssid: "",
        password: "",
        server_ip: "192.168.1.100", // Default
        name: "Nexora Cam " + Math.floor(Math.random() * 1000)
    });

    // Config for Manual/Auto Connection
    const [manualConfig, setManualConfig] = useState<{
        name: string;
        ip: string;
        vflip: boolean;
        type?: string;
        username?: string;
        password?: string;
        port?: string;
    }>({
        name: "New Camera",
        ip: "",
        vflip: false,
        port: "554",
        type: "tapo"
    });

    const handleSoftApProvision = async () => {
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

            // 2. Register on Backend
            await registerCamera(config.name.replace(/\s+/g, '_').toLowerCase(), "unknown");

        } catch (e: any) {
            setError(e.message || "Provisioning failed");
        } finally {
            setLoading(false);
        }
    };

    const handleScan = async () => {
        setScanning(true);
        setError(null);
        try {
            const cameras = await discoverCameras();
            setFoundCameras(cameras);
            if (cameras.length === 0) {
                setError("No cameras found on local network.");
            }
        } catch (e: any) {
            setError("Scan failed. Ensure backend is running.");
        } finally {
            setScanning(false);
        }
    };

    const handleManualRegister = async () => {
        setLoading(true);
        setError(null);
        try {
            await registerCamera(
                manualConfig.name.replace(/\s+/g, '_').toLowerCase(),
                manualConfig.ip,
                manualConfig.vflip
            );
            onOpenChange(false);
            onSuccess();
        } catch (e: any) {
            setError(e.message || "Registration failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] bg-zinc-950 border-white/5">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Camera className="w-5 h-5 text-blue-500" />
                        Add Camera
                    </DialogTitle>
                    <DialogDescription>
                        Connect an existing camera or provision a new one.
                    </DialogDescription>
                </DialogHeader>

                <Tabs defaultValue="manual" value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-3 bg-zinc-900">
                        <TabsTrigger value="manual">Auto / Manual</TabsTrigger>
                        <TabsTrigger value="cctv">Tapo / CCTV</TabsTrigger>
                        <TabsTrigger value="provision">SoftAP</TabsTrigger>
                    </TabsList>

                    {/* TAB 1: MANUAL & AUTO SCAN */}
                    <TabsContent value="manual" className="space-y-4 py-4">
                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                onClick={handleScan}
                                disabled={scanning}
                                className="w-full border-blue-500/20 hover:bg-blue-500/10 hover:text-blue-400"
                            >
                                {scanning ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
                                {scanning ? "Scanning Subnet..." : "Scan Network"}
                            </Button>
                        </div>

                        {foundCameras.length > 0 && (
                            <div className="space-y-2">
                                <Label className="text-xs text-muted-foreground">Discovered Devices</Label>
                                <div className="grid gap-2 max-h-32 overflow-y-auto">
                                    {foundCameras.map((cam) => (
                                        <div
                                            key={cam.ip}
                                            className="flex items-center justify-between p-2 rounded border border-white/5 bg-white/5 hover:bg-white/10 cursor-pointer"
                                            onClick={() => setManualConfig({ ...manualConfig, ip: cam.ip })}
                                        >
                                            <div className="flex items-center gap-2">
                                                <Network className="w-4 h-4 text-green-500" />
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-mono">{cam.ip}</span>
                                                    <span className="text-[10px] text-muted-foreground">{cam.model}</span>
                                                </div>
                                            </div>
                                            <Badge variant="outline" className="text-[10px]">Select</Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="space-y-3 pt-2 border-t border-white/5">
                            <div className="grid gap-2">
                                <Label htmlFor="m-name">Camera Name</Label>
                                <Input
                                    id="m-name"
                                    value={manualConfig.name}
                                    onChange={(e) => setManualConfig({ ...manualConfig, name: e.target.value })}
                                    className="bg-white/5 border-white/10"
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="m-ip">IP Address</Label>
                                <Input
                                    id="m-ip"
                                    value={manualConfig.ip}
                                    onChange={(e) => setManualConfig({ ...manualConfig, ip: e.target.value })}
                                    placeholder="192.168.x.x"
                                    className="bg-white/5 border-white/10"
                                />
                            </div>
                        </div>

                        <Button
                            className="w-full bg-green-600 hover:bg-green-700"
                            onClick={handleManualRegister}
                            disabled={loading || !manualConfig.ip}
                        >
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Connect Camera
                        </Button>
                    </TabsContent>

                    {/* TAB 3: CCTV / RTSP */}
                    <TabsContent value="cctv" className="space-y-4 py-4">
                        <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-xs space-y-2">
                            <div className="flex items-center gap-2 text-zinc-300 font-semibold">
                                <Server className="w-4 h-4" />
                                Support for Tapo, Hikvision, etc.
                            </div>
                            <p className="text-muted-foreground">
                                Ensure <strong>RTSP/ONVIF</strong> is enabled in your camera settings and you have created a camera account.
                            </p>
                        </div>

                        {/* RTSP Auto-Scan Button */}
                        <Button
                            variant="outline"
                            onClick={async () => {
                                setScanningRtsp(true);
                                setError(null);
                                try {
                                    const cameras = await discoverRtspCameras();
                                    setFoundRtsp(cameras);
                                    if (cameras.length === 0) {
                                        setError("No RTSP/CCTV devices found. Check network.");
                                    }
                                } catch (e: any) {
                                    setError("RTSP scan failed. Ensure backend is running.");
                                } finally {
                                    setScanningRtsp(false);
                                }
                            }}
                            disabled={scanningRtsp}
                            className="w-full border-blue-500/20 hover:bg-blue-500/10 hover:text-blue-400"
                        >
                            {scanningRtsp ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
                            {scanningRtsp ? "Scanning RTSP Ports..." : "Auto-Scan Network"}
                        </Button>

                        {/* Discovered RTSP Devices */}
                        {foundRtsp.length > 0 && (
                            <div className="space-y-2">
                                <Label className="text-xs text-muted-foreground">Discovered CCTV/RTSP Devices</Label>
                                <div className="grid gap-2 max-h-32 overflow-y-auto">
                                    {foundRtsp.map((cam) => (
                                        <div
                                            key={cam.ip}
                                            className="flex items-center justify-between p-2 rounded border border-white/5 bg-white/5 hover:bg-white/10 cursor-pointer"
                                            onClick={() => setManualConfig({
                                                ...manualConfig,
                                                ip: cam.ip,
                                                port: String(cam.suggested_port)
                                            })}
                                        >
                                            <div className="flex items-center gap-2">
                                                <Network className="w-4 h-4 text-blue-500" />
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-mono">{cam.ip}</span>
                                                    <span className="text-[10px] text-muted-foreground">
                                                        {cam.type} • Ports: {cam.ports.join(", ")}
                                                    </span>
                                                </div>
                                            </div>
                                            <Badge variant="outline" className="text-[10px]">Select</Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="space-y-3">
                            <div className="grid gap-2">
                                <Label htmlFor="c-type">Camera Brand</Label>
                                <select
                                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 bg-zinc-950 border-white/10"
                                    value={manualConfig.type || "tapo"}
                                    onChange={(e) => setManualConfig({ ...manualConfig, type: e.target.value })}
                                >
                                    <option value="tapo">TP-Link Tapo / Kasa</option>
                                    <option value="hikvision">Hikvision</option>
                                    <option value="dahua">Dahua</option>
                                    <option value="reolink">Reolink</option>
                                    <option value="generic">Generic RTSP</option>
                                </select>
                                <span className="text-[10px] text-muted-foreground">
                                    Official RTSP paths used per manufacturer
                                </span>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="c-ip">IP Address</Label>
                                    <Input
                                        id="c-ip"
                                        placeholder="192.168.1.x"
                                        value={manualConfig.ip}
                                        onChange={(e) => setManualConfig({ ...manualConfig, ip: e.target.value })}
                                        className="bg-zinc-950 border-white/10"
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="c-port">Port (Default 554)</Label>
                                    <Input
                                        id="c-port"
                                        placeholder="554"
                                        value={manualConfig.port || "554"}
                                        onChange={(e) => setManualConfig({ ...manualConfig, port: e.target.value })}
                                        className="bg-zinc-950 border-white/10"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="c-user">Username</Label>
                                    <Input
                                        id="c-user"
                                        placeholder="admin"
                                        value={manualConfig.username || ""}
                                        onChange={(e) => setManualConfig({ ...manualConfig, username: e.target.value })}
                                        className="bg-zinc-950 border-white/10"
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="c-pass">Password</Label>
                                    <Input
                                        id="c-pass"
                                        type="password"
                                        placeholder="••••••"
                                        value={manualConfig.password || ""}
                                        onChange={(e) => setManualConfig({ ...manualConfig, password: e.target.value })}
                                        className="bg-zinc-950 border-white/10"
                                    />
                                </div>
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="c-name">Camera Name</Label>
                                <Input
                                    id="c-name"
                                    value={manualConfig.name}
                                    onChange={(e) => setManualConfig({ ...manualConfig, name: e.target.value })}
                                    className="bg-zinc-950 border-white/10"
                                />
                            </div>
                        </div>

                        <Button
                            className="w-full bg-blue-600 hover:bg-blue-700"
                            onClick={async () => {
                                setLoading(true);
                                setError(null);
                                try {
                                    const cameraType = manualConfig.type || "generic";

                                    // For Tapo cameras, use official pytapo validation
                                    if (cameraType === "tapo") {
                                        console.log(`[Tapo] Using pytapo for ${manualConfig.ip}`);

                                        await registerTapoCamera(
                                            manualConfig.name.replace(/\s+/g, '_').toLowerCase(),
                                            manualConfig.ip,
                                            manualConfig.username || "",
                                            manualConfig.password || "",
                                            "stream1",
                                            manualConfig.vflip
                                        );
                                    } else {
                                        // For other brands, construct RTSP URL manually
                                        const userPart = (manualConfig.username && manualConfig.password)
                                            ? `${manualConfig.username}:${manualConfig.password}@`
                                            : "";
                                        const portPart = manualConfig.port ? `:${manualConfig.port}` : ":554";

                                        const rtspPaths: Record<string, string> = {
                                            "hikvision": "/Streaming/Channels/101",
                                            "dahua": "/cam/realmonitor?channel=1&subtype=0",
                                            "reolink": "/h264Preview_01_main",
                                            "generic": "/"
                                        };
                                        const pathPart = rtspPaths[cameraType] || "/";
                                        const rtspUrl = `rtsp://${userPart}${manualConfig.ip}${portPart}${pathPart}`;

                                        await registerCamera(
                                            manualConfig.name.replace(/\s+/g, '_').toLowerCase(),
                                            rtspUrl,
                                            manualConfig.vflip
                                        );
                                    }

                                    onOpenChange(false);
                                    onSuccess();
                                } catch (e: any) {
                                    // Display validation error from backend
                                    setError(e.message || "Registration failed");
                                } finally {
                                    setLoading(false);
                                }
                            }}
                            disabled={loading || !manualConfig.ip || !manualConfig.username || !manualConfig.password}
                        >
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Connect CCTV
                        </Button>
                    </TabsContent>

                    {/* TAB 2: SOFTAP PROVISIONING */}
                    <TabsContent value="provision">
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

                                <Button
                                    onClick={handleSoftApProvision}
                                    disabled={loading || !config.ssid || !config.server_ip}
                                    className="w-full bg-blue-600 hover:bg-blue-700"
                                >
                                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Wifi className="w-4 h-4 mr-2" />}
                                    Start Handshake
                                </Button>
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
                                <Button
                                    onClick={() => { onOpenChange(false); onSuccess(); }}
                                    className="w-full"
                                >
                                    Done
                                </Button>
                            </div>
                        )}
                    </TabsContent>
                </Tabs>

                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        {error}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
