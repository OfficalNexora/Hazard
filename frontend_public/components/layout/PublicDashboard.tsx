'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import {
    ShieldAlert,
    Map as MapIcon,
    Video,
    Bell,
    LogOut,
    ChevronRight,
    ShieldCheck,
    Compass
} from 'lucide-react';
import { usePublicState } from '@/lib/hooks';
import { cn } from '@/lib/utils';

// Dynamically import map
const PublicMap = dynamic(() => import('@/components/map/PublicMap'), {
    ssr: false,
    loading: () => <div className="h-full w-full bg-zinc-900 animate-pulse flex items-center justify-center text-zinc-500">Loading Satellites...</div>
});

interface PublicDashboardProps {
    onUnpair: () => void;
}

export default function PublicDashboard({ onUnpair }: PublicDashboardProps) {
    // I designed this component as a read-only, high-visibility information radiator.
    // It is specifically optimized for public display screens where readability from a distance is paramount.
    const { state, connected } = usePublicState();
    let alertState = state?.alert?.state || 'SAFE';
    let alertLevel = state?.alert?.value || 0;

    // Fire Override
    if (state?.sensor?.fire) {
        alertState = 'FIRE DETECTED';
        alertLevel = 4;
    }

    return (
        <div className="min-h-screen bg-black text-white selection:bg-blue-500/30">
            {/* Dynamic Header */}
            <header className={cn(
                "sticky top-0 z-50 px-6 py-4 flex items-center justify-between backdrop-blur-md transition-colors duration-500 border-b",
                alertLevel >= 2 ? "bg-red-950/20 border-red-500/20" : "bg-black/50 border-white/5"
            )}>
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "p-2 rounded-lg",
                        alertLevel >= 2 ? "bg-red-500/20" : "bg-blue-500/20"
                    )}>
                        <ShieldCheck className={cn("w-5 h-5", alertLevel >= 2 ? "text-red-400" : "text-blue-400")} />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold tracking-tight">STATION ALPHA</h2>
                        <div className="flex items-center gap-1.5">
                            <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse", connected ? "bg-emerald-500" : "bg-zinc-500")} />
                            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
                                {connected ? 'Sync Connected' : 'Sync Lost'}
                            </span>
                        </div>
                    </div>
                </div>

                <button
                    onClick={onUnpair}
                    className="p-2 hover:bg-white/5 rounded-lg transition-colors text-zinc-500 hover:text-white"
                    title="Disconnect Station"
                >
                    <LogOut className="w-5 h-5" />
                </button>
            </header>

            <main className="p-4 space-y-4 max-w-5xl mx-auto pb-24">
                {/* Alert Banner */}
                <div className={cn(
                    "relative overflow-hidden p-6 rounded-3xl border transition-all duration-700",
                    alertLevel >= 2
                        ? "bg-red-600/10 border-red-500/30 text-red-500 shadow-[0_0_40px_-10px_rgba(239,68,68,0.2)]"
                        : "bg-zinc-900 border-white/5 text-zinc-400"
                )}>
                    <div className="relative z-10 flex items-center justify-between">
                        <div className="space-y-1">
                            <span className="text-[10px] font-black uppercase tracking-[0.3em] opacity-60">Civil Safety Status</span>
                            <h3 className={cn("text-3xl font-black italic", alertLevel >= 2 && "animate-pulse")}>
                                {alertState.toUpperCase()}
                            </h3>
                            <p className="text-sm opacity-80 max-w-[260px]">
                                {state?.alert?.reason || 'System is monitoring for hazards. No immediate action required.'}
                            </p>
                        </div>
                        <div className={cn(
                            "p-4 rounded-2xl border flex items-center justify-center",
                            alertLevel >= 2 ? "border-red-500/30 bg-red-500/20" : "border-white/10 bg-white/5"
                        )}>
                            <Bell className={cn("w-8 h-8", alertLevel >= 2 && "animate-bounce")} />
                        </div>
                    </div>
                </div>

                {/* Live Video & Map Grid */}
                <div className="grid gap-4 md:grid-cols-2">
                    {/* Live Feed */}
                    <div className="bg-zinc-900 rounded-3xl border border-white/5 overflow-hidden flex flex-col group">
                        <div className="p-4 flex items-center justify-between bg-zinc-800/20">
                            <div className="flex items-center gap-2">
                                <Video className="w-4 h-4 text-emerald-400" />
                                <span className="text-xs font-bold tracking-wider">LIVE NODE-01</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded-full bg-red-500 text-[9px] font-black animate-pulse">REC</span>
                            </div>
                        </div>
                        <div className="relative aspect-video bg-black flex items-center justify-center">
                            {/* MJPEG Stream from Backend */}
                            <img
                                src="http://localhost:8000/api/video_feed"
                                alt="Live Camera Feed"
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                    (e.target as any).src = 'https://images.unsplash.com/photo-1544006659-f0b21f04cb1d?q=80&w=2070&auto=format&fit=crop';
                                    (e.target as any).className = 'w-full h-full object-cover opacity-20 grayscale';
                                }}
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none" />
                            <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end opacity-0 group-hover:opacity-100 transition-opacity">
                                <div className="text-[10px] font-mono text-white/50">40.7128° N, 74.0060° W</div>
                            </div>
                        </div>
                    </div>

                    {/* Hazard Map */}
                    <div className="bg-zinc-900 rounded-3xl border border-white/5 overflow-hidden flex flex-col h-[300px] md:h-auto">
                        <div className="p-4 flex items-center gap-2 bg-zinc-800/20">
                            <MapIcon className="w-4 h-4 text-blue-400" />
                            <span className="text-xs font-bold tracking-wider">SAFETY ZONE MAP</span>
                        </div>
                        <div className="flex-1 relative">
                            <PublicMap />
                        </div>
                    </div>
                </div>

                {/* Recent Hazards List */}
                <div className="bg-zinc-900/50 rounded-3xl border border-white/5 p-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-xs font-black tracking-widest uppercase text-zinc-500">Hazard Detection Stream</h4>
                        <div className="h-0.5 flex-1 mx-4 bg-white/5" />
                    </div>

                    <div className="space-y-3">
                        {state?.detections.slice(0, 3).map((det, i) => (
                            <div key={i} className="flex items-center justify-between p-3 rounded-2xl bg-white/5 border border-white/5 animate-in slide-in-from-bottom-2">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-orange-500/20 flex items-center justify-center">
                                        <ShieldAlert className="w-5 h-5 text-orange-400" />
                                    </div>
                                    <div>
                                        <h5 className="text-sm font-bold uppercase">{det.class}</h5>
                                        <p className="text-[10px] text-zinc-500">Detected in Sector A-1</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-xs font-mono text-orange-400 font-black">{(det.confidence * 100).toFixed(0)}%</div>
                                    <div className="text-[9px] text-zinc-600">{new Date().toLocaleTimeString()}</div>
                                </div>
                            </div>
                        ))}
                        {(!state?.detections || state.detections.length === 0) && (
                            <div className="text-center py-6 text-zinc-600 text-sm italic">
                                Scanning area for potential threats...
                            </div>
                        )}
                    </div>
                </div>
            </main>

            {/* Floating CTA */}
            <div className="fixed bottom-6 left-6 right-6 z-40">
                <button className="w-full h-14 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black shadow-[0_20px_40px_-10px_rgba(37,99,235,0.4)] transition-all flex items-center justify-center gap-2 active:scale-95 group">
                    VIEW SAFE ASSEMBLY POINTS
                    <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
            </div>
        </div>
    );
}
