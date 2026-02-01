'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
    Settings as SettingsIcon,
    Save,
    RotateCcw,
    ShieldCheck,
    Info,
    AlertOctagon,
    Key
} from "lucide-react";
import { useSettings, useAccessCode } from "@/lib/hooks";

export default function SettingsPage() {
    const { settings, loading, update, refresh } = useSettings();
    const { code, loading: codeLoading } = useAccessCode();
    const [localSettings, setLocalSettings] = useState<any>(null);

    useEffect(() => {
        if (settings) {
            setLocalSettings(settings);
        }
    }, [settings]);

    if (loading && !localSettings) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    const handleSave = async () => {
        const success = await update(localSettings);
        if (success) {
            alert("Settings saved successfully!");
        } else {
            alert("Failed to save settings.");
        }
    };

    return (
        <div className="space-y-6 max-w-4xl">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
                        <SettingsIcon className="h-8 w-8 text-primary" />
                        System Configuration
                    </h1>
                    <p className="text-muted-foreground">Manage AI thresholds, alert behaviors, and system maintenance.</p>
                </div>
                <Button onClick={handleSave} className="gap-2">
                    <Save className="h-4 w-4" />
                    Save Changes
                </Button>
            </div>

            <div className="grid gap-6">
                {/* Public Portal Access */}
                <Card className="border-primary/20 bg-primary/5">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Key className="h-5 w-5 text-primary" />
                            Public Portal Pairing
                        </CardTitle>
                        <CardDescription>Use this code to connect the Public Portal to this local server.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-primary/30 rounded-xl bg-background/50">
                            <span className="text-sm text-muted-foreground mb-2 uppercase tracking-widest font-semibold">Access Code</span>
                            {codeLoading ? (
                                <div className="h-12 w-32 bg-muted animate-pulse rounded-md" />
                            ) : (
                                <div className="text-5xl font-black tracking-[0.5em] text-primary font-mono ml-4">
                                    {code}
                                </div>
                            )}
                            <p className="mt-4 text-xs text-center text-muted-foreground">
                                Enter this code on the <strong>Public User Portal</strong> screen to view live hazards and alerts from this station.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* AI Thresholds */}
                <Card>
                    <CardHeader>
                        <CardTitle>AI Logic & Thresholds</CardTitle>
                        <CardDescription>Configure how the vision system evaluates hazards.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label>Minimum Confidence Threshold</Label>
                                <span className="font-mono text-sm font-bold text-primary">
                                    {Math.round((localSettings?.confidence_threshold || 0) * 100)}%
                                </span>
                            </div>
                            <Slider
                                value={[(localSettings?.confidence_threshold || 0) * 100]}
                                min={10}
                                max={95}
                                step={5}
                                onValueChange={(val) => setLocalSettings({ ...localSettings, confidence_threshold: val[0] / 100 })}
                            />
                            <p className="text-xs text-muted-foreground italic flex items-center gap-1">
                                <Info className="h-3 w-3" />
                                Higher threshold reduces false positives but may miss subtle hazards.
                            </p>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label>Analysis Interval (ms)</Label>
                                <Input
                                    type="number"
                                    value={localSettings?.analysis_interval_ms || 1000}
                                    onChange={(e) => setLocalSettings({ ...localSettings, analysis_interval_ms: parseInt(e.target.value) })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Batch Size</Label>
                                <Input type="number" value="1" disabled />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Alert Behavior */}
                <Card>
                    <CardHeader>
                        <CardTitle>Alert & Evacuation Behavior</CardTitle>
                        <CardDescription>Define how the system responds to detected threats.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between space-x-2">
                            <Label htmlFor="hb" className="flex flex-col space-y-1">
                                <span>Enable Control Unit Heartbeat</span>
                                <span className="font-normal text-xs text-muted-foreground truncate">
                                    Monitor ESP32-Main connectivity status in real-time.
                                </span>
                            </Label>
                            <Switch id="hb" defaultChecked />
                        </div>

                        <div className="space-y-2">
                            <Label>Default Alert Mode</Label>
                            <select
                                className="w-full p-2 rounded-md border border-input bg-background"
                                value={localSettings?.alert_mode || "Visual"}
                                onChange={(e) => setLocalSettings({ ...localSettings, alert_mode: e.target.value })}
                            >
                                <option>Silent (Log Only)</option>
                                <option>Visual (Strobe LED)</option>
                                <option>Audible (Siren + Voice)</option>
                                <option>Critical (Auto-Messaging)</option>
                            </select>
                        </div>
                    </CardContent>
                </Card>

                {/* Security / Danger Zone */}
                <Card className="border-red-500/20 bg-red-500/5">
                    <CardHeader>
                        <CardTitle className="text-red-500 flex items-center gap-2">
                            <AlertOctagon className="h-5 w-5" />
                            Maintenance & Reset
                        </CardTitle>
                        <CardDescription>Critical operations that affect system stability.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium">Restart Vision Pipeline</p>
                                <p className="text-xs text-muted-foreground">Reload YOLO models and reset video stream.</p>
                            </div>
                            <Button variant="outline" size="sm" onClick={() => alert("Pipeline reset triggered.")}>
                                <RotateCcw className="h-4 w-4 mr-2" />
                                Reset
                            </Button>
                        </div>
                        <div className="pt-4 border-t border-red-500/20">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="font-medium text-red-500">Factory Reset</p>
                                    <p className="text-xs text-muted-foreground">Wipe all history logs and reset configuration.</p>
                                </div>
                                <Button variant="destructive" size="sm">
                                    Wipe Data
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
