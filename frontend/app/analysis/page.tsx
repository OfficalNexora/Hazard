'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    LineChart,
    Line,
    Cell
} from 'recharts';
import {
    TrendingUp,
    History,
    AlertCircle,
    Clock,
    ShieldAlert
} from "lucide-react";
import { useHistory } from "@/lib/hooks";
import { Badge } from "@/components/ui/badge";

const COLOR_MAP: Record<string, string> = {
    'Fire': '#ef4444',
    'Smoke': '#64748b',
    'Flood': '#3b82f6',
    'Landslide': '#f97316',
    'Falling Debris': '#eab308',
    'Explosion': '#dc2626',
    'Collapsed Structure': '#991b1b',
    'Industrial Accident': '#a855f7',
    'Unknown': '#94a3b8'
};

export default function AnalysisPage() {
    const { history, loading } = useHistory(200);

    const stats = useMemo(() => {
        if (!history.length) return { classData: [], timelineData: [] };

        // Group by class
        const counts: Record<string, number> = {};
        history.forEach(d => {
            counts[d.class] = (counts[d.class] || 0) + 1;
        });

        const classData = Object.entries(counts).map(([name, value]) => ({
            name,
            value,
            fill: COLOR_MAP[name] || COLOR_MAP.Unknown
        })).sort((a, b) => b.value - a.value);

        // Group by minute (relative)
        const timeline: Record<string, number> = {};
        history.forEach(d => {
            if (d.timestamp) {
                const date = new Date(d.timestamp * 1000);
                const key = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                timeline[key] = (timeline[key] || 0) + 1;
            }
        });

        const timelineData = Object.entries(timeline).map(([time, count]) => ({
            time,
            count
        })).reverse().slice(-20);

        return { classData, timelineData };
    }, [history]);

    if (loading && !history.length) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
                    <TrendingUp className="h-8 w-8 text-primary" />
                    Hazard Intelligence Analysis
                </h1>
                <p className="text-muted-foreground">Historical breakdown of detected threats and system responses.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {/* Total Events */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                        <CardTitle className="text-sm font-medium">Logged Detections</CardTitle>
                        <History className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{history.length}</div>
                        <p className="text-xs text-muted-foreground">Events stored in local SQLite database</p>
                    </CardContent>
                </Card>

                {/* Top Threat */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                        <CardTitle className="text-sm font-medium">Primary Hazard</CardTitle>
                        <AlertCircle className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.classData[0]?.name || 'None'}</div>
                        <p className="text-xs text-muted-foreground">Most frequent detection class</p>
                    </CardContent>
                </Card>

                {/* Avg Confidence */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                        <CardTitle className="text-sm font-medium">Avg. Confidence</CardTitle>
                        <ShieldAlert className="h-4 w-4 text-emerald-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {history.length ? (history.reduce((acc, curr) => acc + curr.confidence, 0) / history.length * 100).toFixed(1) : '0'}%
                        </div>
                        <p className="text-xs text-muted-foreground">AI model certainty average</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Hazard Distribution Chart */}
                <Card className="col-span-1">
                    <CardHeader>
                        <CardTitle>Hazard Distribution</CardTitle>
                        <CardDescription>Frequency of different hazard classes detected.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats.classData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                                    itemStyle={{ color: '#f8fafc' }}
                                />
                                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                    {stats.classData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Activity Timeline */}
                <Card className="col-span-1">
                    <CardHeader>
                        <CardTitle>Activity Timeline</CardTitle>
                        <CardDescription>Detection events over time (last 20 buckets).</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={stats.timelineData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                                <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                                    itemStyle={{ color: '#f8fafc' }}
                                />
                                <Line type="monotone" dataKey="count" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Raw Logs Table */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>Historical Event Logs</CardTitle>
                            <CardDescription>Recent raw entries from system.db</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="relative w-full overflow-auto max-h-[400px]">
                        <table className="w-full caption-bottom text-sm">
                            <thead className="[&_tr]:border-b border-muted">
                                <tr className="transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <th className="h-10 px-2 text-left align-middle font-medium text-muted-foreground w-[150px]">Time</th>
                                    <th className="h-10 px-2 text-left align-middle font-medium text-muted-foreground">Hazard Class</th>
                                    <th className="h-10 px-2 text-left align-middle font-medium text-muted-foreground">Confidence</th>
                                    <th className="h-10 px-2 text-right align-middle font-medium text-muted-foreground">Frame ID</th>
                                </tr>
                            </thead>
                            <tbody className="[&_tr:last-child]:border-0">
                                {history.map((d, i) => (
                                    <tr key={i} className="border-b border-muted transition-colors hover:bg-muted/30">
                                        <td className="p-2 align-middle font-mono text-xs">
                                            {d.timestamp ? new Date(d.timestamp * 1000).toLocaleString() : 'N/A'}
                                        </td>
                                        <td className="p-2 align-middle">
                                            <div className="flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLOR_MAP[d.class] || '#94a3b8' }} />
                                                {d.class}
                                            </div>
                                        </td>
                                        <td className="p-2 align-middle font-mono">
                                            <Badge variant="outline" className="font-mono">{(d.confidence * 100).toFixed(1)}%</Badge>
                                        </td>
                                        <td className="p-2 align-middle text-right font-mono text-muted-foreground">#{d.frame_id}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
