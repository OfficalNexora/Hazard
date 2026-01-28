"use client";

import dynamic from "next/dynamic";
import { Card } from "@/components/ui/card";

// Dynamically import Leaflet map to avoid server-side errors
const LiveMap = dynamic(() => import("@/components/map/LiveMap"), {
    ssr: false,
    loading: () => (
        <div className="flex h-full w-full items-center justify-center bg-muted/20 animate-pulse">
            <span className="text-sm font-medium text-muted-foreground">Initializing Satellites...</span>
        </div>
    ),
});

export default function MapPage() {
    return (
        <div className="flex h-[calc(100vh-8rem)] flex-col space-y-4">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight text-foreground">Live Telemetry</h1>
                <div className="flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                    </span>
                    <span className="text-sm font-medium text-emerald-500">Tracking Active</span>
                </div>
            </div>

            <Card className="flex-1 overflow-hidden border-border bg-card p-0 shadow-lg">
                <LiveMap />
            </Card>
        </div>
    );
}
