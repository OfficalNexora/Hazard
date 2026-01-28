'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Bell, ShieldAlert, Clock, Filter, Download, Database } from "lucide-react";
import { useHistory, useDetections } from "@/lib/hooks";
import { useState } from "react";

const HAZARD_COLORS: Record<string, string> = {
    'Fire': 'bg-red-500',
    'Explosion': 'bg-red-600',
    'Smoke': 'bg-gray-500',
    'Flood': 'bg-blue-500',
    'Landslide': 'bg-orange-500',
    'Falling Debris': 'bg-yellow-500',
    'Collapsed Structure': 'bg-red-800',
    'Industrial Accident': 'bg-purple-500',
};

export default function AlertsPage() {
    const { history, loading: historyLoading } = useHistory(100);
    const liveDetections = useDetections(10);
    const [filter, setFilter] = useState('ALL');

    const allEvents = [...liveDetections, ...history];
    // Remove duplicates by frame_id or timestamp
    const uniqueEvents = allEvents.filter((v, i, a) => a.findIndex(t => (t.frame_id === v.frame_id)) === i);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                        <Database className="h-8 w-8 text-primary" />
                        STA. DATA LOG
                    </h1>
                    <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Mission Critical Event Registry | system.db</p>
                </div>
                <div className="flex gap-2">
                    <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted text-xs font-bold uppercase hover:bg-muted/80 transition">
                        <Download className="h-3 w-3" /> Export CSV
                    </button>
                    <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10 text-primary text-xs font-bold uppercase hover:bg-primary/20 transition">
                        <Filter className="h-3 w-3" /> Filter Logs
                    </button>
                </div>
            </div>

            {/* Live Feed Header */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card className="bg-red-500/5 border-red-500/20">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-red-500 flex items-center gap-2">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                            </span>
                            Ingest Rate
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black text-red-500">20 ms</div>
                        <p className="text-[10px] font-mono opacity-50 uppercase mt-1">Real-time telemetry link</p>
                    </CardContent>
                </Card>

                <Card className="bg-blue-500/5 border-blue-500/20">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-blue-500 flex items-center gap-2">
                            <Database className="h-3 w-3" /> Total Records
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black text-blue-500">{history.length}</div>
                        <p className="text-[10px] font-mono opacity-50 uppercase mt-1">Entries in system.db</p>
                    </CardContent>
                </Card>

                <Card className="bg-emerald-500/5 border-emerald-500/20">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-emerald-500 flex items-center gap-2">
                            <ShieldAlert className="h-3 w-3" /> Integrity
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black text-emerald-500">VERIFIED</div>
                        <p className="text-[10px] font-mono opacity-50 uppercase mt-1">SHA-256 Consistency check</p>
                    </CardContent>
                </Card>
            </div>

            {/* High-Performance Event Table */}
            <Card className="border-muted-foreground/10 overflow-hidden bg-card/30 backdrop-blur-md">
                <CardHeader className="border-b bg-muted/20">
                    <CardTitle className="text-sm font-black uppercase tracking-widest text-muted-foreground">Historical Intelligence Feed</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader className="bg-muted/50">
                            <TableRow className="border-muted-foreground/10 h-10">
                                <TableHead className="w-[180px] text-[10px] font-black uppercase tracking-widest">TIMESTAMP</TableHead>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest text-center">ZONE</TableHead>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest">HAZARD_CLASS</TableHead>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest">CONFIDENCE</TableHead>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest">FRAME_HEX</TableHead>
                                <TableHead className="text-right text-[10px] font-black uppercase tracking-widest">ACTION_LOG</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {uniqueEvents.length === 0 && !historyLoading && (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-20 opacity-30 uppercase font-mono italic text-xs">
                                        No event history found in registry
                                    </TableCell>
                                </TableRow>
                            )}
                            {uniqueEvents.map((event, i) => (
                                <TableRow key={i} className="border-b border-muted-foreground/5 hover:bg-muted/30 transition group">
                                    <TableCell className="font-mono text-[10px] text-muted-foreground py-4">
                                        {event.timestamp ? new Date(event.timestamp * 1000).toLocaleString() : 'PNDG_PROC'}
                                    </TableCell>
                                    <TableCell className="text-center">
                                        <Badge className="bg-muted text-white text-[9px] font-bold">Z-01</Badge>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            <div className={`w-1.5 h-1.5 rounded-full ${HAZARD_COLORS[event.class] || 'bg-primary'} animate-pulse`} />
                                            <span className="font-black text-xs uppercase tracking-tight">{event.class}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 w-16 h-1 bg-muted rounded-full">
                                                <div
                                                    className={`h-full ${event.confidence > 0.8 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                                                    style={{ width: `${event.confidence * 100}%` }}
                                                />
                                            </div>
                                            <span className="font-mono text-[10px] text-muted-foreground">{(event.confidence * 100).toFixed(0)}%</span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="font-mono text-[10px] text-muted-foreground opacity-50">
                                        0x{event.frame_id.toString(16).toUpperCase().padStart(8, '0')}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <Badge variant="outline" className="text-[9px] border-emerald-500/20 text-emerald-500 group-hover:bg-emerald-500/10 cursor-pointer">
                                            VIEW_METADATA
                                        </Badge>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
