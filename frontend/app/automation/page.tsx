'use client';

import { useState, useEffect } from 'react';
import {
    Terminal,
    Zap,
    Play,
    Plus,
    Trash2,
    Smartphone,
    RefreshCcw,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Code2,
    Hash
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface AdbDevice {
    id: string;
    status: string;
}

interface AdbScript {
    id: number;
    label: string;
    command: string;
    category: string;
}

export default function AutomationPage() {
    const [devices, setDevices] = useState<AdbDevice[]>([]);
    const [scripts, setScripts] = useState<AdbScript[]>([]);
    const [selectedDevice, setSelectedDevice] = useState<string>("");
    const [loading, setLoading] = useState(true);
    const [scanning, setScanning] = useState(false);
    const [executing, setExecuting] = useState<number | null>(null);
    const [isAdding, setIsAdding] = useState(false);

    // New Script Form
    const [newScript, setNewScript] = useState({
        label: "",
        command: "",
        category: "general"
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [devRes, scrRes] = await Promise.all([
                fetch("http://localhost:8000/api/adb/devices"),
                fetch("http://localhost:8000/api/adb/scripts")
            ]);

            const devData = await devRes.json();
            const scrData = await scrRes.json();

            setDevices(devData.devices || []);
            setScripts(scrData || []);

            if (devData.devices?.length > 0 && !selectedDevice) {
                setSelectedDevice(devData.devices[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoading(false);
        }
    };

    const scanDevices = async () => {
        setScanning(true);
        try {
            const res = await fetch("http://localhost:8000/api/adb/devices");
            const data = await res.json();
            setDevices(data.devices || []);
            if (data.devices?.length > 0 && !selectedDevice) {
                setSelectedDevice(data.devices[0].id);
            }
        } catch (error) {
            console.error("Scan failed", error);
        } finally {
            setScanning(false);
        }
    };

    const handleAddScript = async () => {
        try {
            const res = await fetch("http://localhost:8000/api/adb/scripts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(newScript)
            });
            if (res.ok) {
                const updated = await fetch("http://localhost:8000/api/adb/scripts");
                setScripts(await updated.json());
                setIsAdding(false);
                setNewScript({ label: "", command: "", category: "general" });
            }
        } catch (error) {
            console.error("Add failed", error);
        }
    };

    const handleDeleteScript = async (id: number) => {
        try {
            const res = await fetch(`http://localhost:8000/api/adb/scripts/${id}`, {
                method: "DELETE"
            });
            if (res.ok) {
                setScripts(scripts.filter(s => s.id !== id));
            }
        } catch (error) {
            console.error("Delete failed", error);
        }
    };

    const executeScript = async (scriptId: number) => {
        if (!selectedDevice) {
            alert("Please select a device first");
            return;
        }

        setExecuting(scriptId);
        try {
            const res = await fetch("http://localhost:8000/api/adb/execute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    device_id: selectedDevice,
                    script_id: scriptId
                })
            });
            const data = await res.json();
            if (res.ok) {
                console.log("Execution result:", data);
                // Optionally show toast or notification
            } else {
                alert(`Execution failed: ${data.detail}`);
            }
        } catch (error) {
            console.error("Execution error", error);
        } finally {
            setExecuting(null);
        }
    };

    return (
        <div className="flex-1 space-y-6 p-8 pt-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                        <Terminal className="text-primary h-8 w-8" />
                        ADB Automation
                    </h2>
                    <p className="text-muted-foreground">Manage Android nodes and execute custom operational scripts.</p>
                </div>

                <div className="flex items-center gap-3">
                    <Button variant="outline" size="sm" onClick={scanDevices} disabled={scanning} className="gap-2">
                        {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
                        Scan Devices
                    </Button>
                    <Dialog open={isAdding} onOpenChange={setIsAdding}>
                        <DialogTrigger asChild>
                            <Button className="gap-2">
                                <Plus size={18} />
                                New Script
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[425px] bg-zinc-950 border-zinc-800">
                            <DialogHeader>
                                <DialogTitle>Add Automation Script</DialogTitle>
                                <DialogDescription>
                                    Define a new shell command to be executed via ADB.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="space-y-2">
                                    <Label>Script Label</Label>
                                    <Input
                                        value={newScript.label}
                                        onChange={e => setNewScript({ ...newScript, label: e.target.value })}
                                        placeholder="e.g. Unlock Screen"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Shell Command</Label>
                                    <div className="relative">
                                        <div className="absolute left-3 top-3 text-muted-foreground">
                                            <Code2 size={16} />
                                        </div>
                                        <Input
                                            className="pl-10 font-mono text-xs"
                                            value={newScript.command}
                                            onChange={e => setNewScript({ ...newScript, command: e.target.value })}
                                            placeholder="input keyevent 82"
                                        />
                                    </div>
                                    <p className="text-[10px] text-muted-foreground">Command will be prefixed with 'adb shell'</p>
                                </div>
                                <div className="space-y-2">
                                    <Label>Category</Label>
                                    <Select
                                        value={newScript.category}
                                        onValueChange={val => setNewScript({ ...newScript, category: val })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Category" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="general">General</SelectItem>
                                            <SelectItem value="security">Security</SelectItem>
                                            <SelectItem value="maintenance">Maintenance</SelectItem>
                                            <SelectItem value="test">Diagnostics</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <DialogFooter>
                                <Button onClick={handleAddScript}>Save Script</Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                {/* Device Selector */}
                <Card className="md:col-span-1 bg-zinc-900/40 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-xl flex items-center gap-2">
                            <Smartphone className="text-emerald-500" size={20} />
                            Active Nodes
                        </CardTitle>
                        <CardDescription>Select target device for execution</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {devices.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-8 text-center space-y-3">
                                <AlertCircle className="h-10 w-10 text-zinc-700" />
                                <div className="space-y-1">
                                    <p className="text-sm font-medium">No devices found</p>
                                    <p className="text-xs text-muted-foreground">Connect via USB or ADB-over-WiFi</p>
                                </div>
                                <Button variant="outline" size="sm" onClick={scanDevices}>Retry Discovery</Button>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {devices.map(device => (
                                    <button
                                        key={device.id}
                                        onClick={() => setSelectedDevice(device.id)}
                                        className={cn(
                                            "w-full flex items-center justify-between p-3 rounded-lg border transition-all",
                                            selectedDevice === device.id
                                                ? "bg-primary/10 border-primary shadow-[0_0_15px_rgba(var(--primary-rgb),0.1)]"
                                                : "bg-muted/10 border-zinc-800 hover:border-zinc-700 hover:bg-muted/20"
                                        )}
                                    >
                                        <div className="flex items-center gap-3 text-left">
                                            <div className={cn(
                                                "h-2 w-2 rounded-full",
                                                device.status === 'device' ? "bg-emerald-500" : "bg-amber-500"
                                            )} />
                                            <div>
                                                <p className="text-sm font-bold font-mono">{device.id}</p>
                                                <p className="text-[10px] text-zinc-500 uppercase">{device.status}</p>
                                            </div>
                                        </div>
                                        {selectedDevice === device.id && (
                                            <CheckCircle2 className="text-primary h-4 w-4" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}

                        <div className="pt-4 border-t border-zinc-800">
                            <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                                <p className="text-[10px] text-blue-400 font-medium lowercase">
                                    nexora is scanning for devices on standard 5555 port and usb interfaces.
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Script Library */}
                <Card className="md:col-span-2 bg-zinc-900/40 border-zinc-800">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div className="space-y-1">
                            <CardTitle className="text-xl flex items-center gap-2">
                                <Zap className="text-amber-500" size={20} />
                                Script Library
                            </CardTitle>
                            <CardDescription>Labeled automation sequences</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-zinc-500">{scripts.length} Total</span>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {scripts.length === 0 ? (
                            <div className="text-center py-20 border-2 border-dashed border-zinc-800 rounded-xl">
                                <p className="text-muted-foreground italic text-sm">No scripts added yet. Click 'New Script' to begin.</p>
                            </div>
                        ) : (
                            <div className="grid gap-3">
                                {scripts.map(script => (
                                    <div
                                        key={script.id}
                                        className="group flex items-center justify-between p-4 rounded-xl bg-zinc-950 border border-zinc-800 hover:border-zinc-700 transition-all"
                                    >
                                        <div className="flex items-center gap-4 flex-1">
                                            <div className="h-10 w-10 rounded-lg bg-zinc-900 flex items-center justify-center border border-zinc-800 group-hover:bg-primary/5 group-hover:border-primary/20 transition-colors">
                                                <Hash className="text-zinc-600 group-hover:text-primary" size={20} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <h4 className="font-bold text-sm truncate">{script.label}</h4>
                                                    <span className="text-[9px] bg-zinc-900 px-1.5 py-0.5 rounded text-zinc-500 uppercase font-bold border border-zinc-800">
                                                        {script.category}
                                                    </span>
                                                </div>
                                                <p className="text-[10px] font-mono text-zinc-500 truncate mt-0.5">
                                                    $ adb shell {script.command}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="outline"
                                                size="icon"
                                                className="h-9 w-9 text-zinc-600 hover:text-red-500 border-zinc-800"
                                                onClick={() => handleDeleteScript(script.id)}
                                            >
                                                <Trash2 size={16} />
                                            </Button>
                                            <Button
                                                className="gap-2 px-4"
                                                disabled={executing === script.id || !selectedDevice}
                                                onClick={() => executeScript(script.id)}
                                            >
                                                {executing === script.id ? (
                                                    <Loader2 size={16} className="animate-spin" />
                                                ) : (
                                                    <Play size={16} fill="currentColor" />
                                                )}
                                                Execute
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
