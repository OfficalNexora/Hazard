"use client";

import { useState, useEffect } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger
} from "@/components/ui/dialog";
import { Wifi, Smartphone, Plus, RefreshCw, Trash2, Cpu, Laptop } from "lucide-react";
import { useDevices, useWorkers } from "@/lib/hooks";
import { classifyWorker } from "@/lib/api";

export default function DevicesPage() {
    const devices = useDevices();
    const workers = useWorkers();

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground uppercase">Device Management</h1>
                    <p className="text-sm text-muted-foreground font-mono">Infrastructure Control and Cluster Orchestration</p>
                </div>
            </div>

            <Tabs defaultValue="cluster" className="w-full">
                <TabsList className="bg-muted/40 p-1 border border-muted-foreground/10 h-12">
                    <TabsTrigger value="cluster" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold uppercase text-xs px-8">
                        <Laptop className="mr-2 h-4 w-4" /> Cluster Nodes
                    </TabsTrigger>
                </TabsList>

                {/* CLUSTER NODES TAB */}
                <TabsContent value="cluster" className="mt-6">
                    <Card className="border-primary/10 bg-primary/2">
                        <CardHeader>
                            <CardTitle className="text-lg font-black tracking-widest uppercase">Intel Distributed Cluster</CardTitle>
                            <CardDescription className="text-xs font-mono uppercase">Assign specialized roles to connected worker laptops</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-muted/50">
                                        <TableHead className="font-bold text-primary">NODE ID</TableHead>
                                        <TableHead>WORKER NAME</TableHead>
                                        <TableHead>CLASSIFICATION</TableHead>
                                        <TableHead>STATUS</TableHead>
                                        <TableHead className="text-right">ACTIONS</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {workers.map((worker) => (
                                        <TableRow key={worker.worker_id} className="hover:bg-primary/5 border-b border-primary/5">
                                            <TableCell className="font-mono text-xs text-primary">{worker.worker_id.split('_')[0]}</TableCell>
                                            <TableCell className="font-bold">{worker.name}</TableCell>
                                            <TableCell>
                                                <select
                                                    className="bg-muted px-2 py-1 rounded text-xs font-bold border border-muted-foreground/20"
                                                    onChange={(e) => classifyWorker(worker.worker_id, e.target.value)}
                                                >
                                                    <option value="GPU Computing">GPU Computing</option>
                                                    <option value="Tracker">Tracker</option>
                                                    <option value="Logic">Logic Processing</option>
                                                </select>
                                            </TableCell>
                                            <TableCell>
                                                <Badge className="bg-emerald-500 uppercase text-[10px]">Active</Badge>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <Button variant="ghost" size="sm" className="text-[10px] font-bold uppercase">Configure</Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {workers.length === 0 && (
                                        <TableRow>
                                            <TableCell colSpan={5} className="text-center py-10 opacity-30 text-xs uppercase italic">No cluster workers detected</TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
