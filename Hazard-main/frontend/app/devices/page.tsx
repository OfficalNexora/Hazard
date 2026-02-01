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
import { Wifi, Smartphone, Plus, RefreshCw, Trash2, Cpu, MessageSquare, PhoneCall, Laptop } from "lucide-react";
import { useDevices, useWorkers } from "@/lib/hooks";
import { addGsmContact, deleteGsmContact, fetchGsmContacts, classifyWorker } from "@/lib/api";

export default function DevicesPage() {
    const devices = useDevices();
    const workers = useWorkers();
    const [contacts, setContacts] = useState<{ sms: any[], call: any[] }>({ sms: [], call: [] });

    // Modal State
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [modalMode, setModalMode] = useState<'sms' | 'call'>('sms');
    const [newNumber, setNewNumber] = useState('');
    const [newName, setNewName] = useState('');
    const [newMessage, setNewMessage] = useState('');
    const [newCategory, setNewCategory] = useState('general');
    const [error, setError] = useState('');

    useEffect(() => {
        refreshContacts();
    }, []);

    const refreshContacts = async () => {
        const data = await fetchGsmContacts();
        setContacts(data);
    };

    const validatePhNumber = (num: string) => {
        // Simple PH Format: +639XXXXXXXXX or 09XXXXXXXXX
        const regex = /^(09|\+639)\d{9}$/;
        return regex.test(num.replace(/\s/g, ''));
    };

    const handleAddContact = async () => {
        if (!validatePhNumber(newNumber)) {
            setError("Invalid Format. Use +639... or 09...");
            return;
        }
        await addGsmContact(modalMode, newNumber, newName, newMessage, newCategory);
        setIsAddModalOpen(false);
        setNewNumber('');
        setNewName('');
        setNewMessage('');
        setNewCategory('general');
        setError('');
        refreshContacts();
    };

    const handleDeleteContact = async (number: string) => {
        if (confirm(`Remove ${number} from emergency list?`)) {
            await deleteGsmContact(number);
            refreshContacts();
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground uppercase">Device Management</h1>
                    <p className="text-sm text-muted-foreground font-mono">Infrastructure Control and Cluster Orchestration</p>
                </div>
            </div>

            <Tabs defaultValue="cluster" className="w-full">
                <TabsList className="grid w-full grid-cols-3 bg-muted/40 p-1 border border-muted-foreground/10 h-12">
                    <TabsTrigger value="cluster" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold uppercase text-xs">
                        <Laptop className="mr-2 h-4 w-4" /> Cluster Nodes
                    </TabsTrigger>
                    <TabsTrigger value="message" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white font-bold uppercase text-xs">
                        <MessageSquare className="mr-2 h-4 w-4" /> SMS Monitoring
                    </TabsTrigger>
                    <TabsTrigger value="call" className="data-[state=active]:bg-red-600 data-[state=active]:text-white font-bold uppercase text-xs">
                        <PhoneCall className="mr-2 h-4 w-4" /> Emergency Calls
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

                {/* SMS MONITORING TAB */}
                <TabsContent value="message" className="mt-6">
                    <Card className="border-blue-500/10 bg-blue-500/2">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-lg font-black tracking-widest uppercase text-blue-500">SMS Alert Registry</CardTitle>
                                <CardDescription className="text-xs font-mono">Contacts designated for real-time text broadcast</CardDescription>
                            </div>
                            <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={() => { setModalMode('sms'); setIsAddModalOpen(true); }}>
                                <Plus className="h-4 w-4 mr-2" /> ADD CONTACT
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-blue-500/10">
                                        <TableHead className="text-blue-500">RECIPIENT</TableHead>
                                        <TableHead>CATEGORY</TableHead>
                                        <TableHead>PHONE NUMBER</TableHead>
                                        <TableHead>CUSTOM MESSAGE</TableHead>
                                        <TableHead className="text-right">MGMT</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {contacts.sms.map((c, i) => (
                                        <TableRow key={i} className="hover:bg-blue-500/5">
                                            <TableCell className="font-bold">{c.name}</TableCell>
                                            <TableCell><Badge variant="outline" className="text-[10px] uppercase">{c.category}</Badge></TableCell>
                                            <TableCell className="font-mono text-xs">{c.number}</TableCell>
                                            <TableCell className="text-xs italic text-muted-foreground">{c.message || '-- System Default --'}</TableCell>
                                            <TableCell className="text-right">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="text-red-500 hover:bg-red-500/10"
                                                    onClick={() => handleDeleteContact(c.number)}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* EMERGENCY CALLS TAB */}
                <TabsContent value="call" className="mt-6">
                    <Card className="border-red-500/10 bg-red-500/2">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-lg font-black tracking-widest uppercase text-red-500">Call Dispatch List</CardTitle>
                                <CardDescription className="text-xs font-mono">Mission-critical targets for automated voice alerts</CardDescription>
                            </div>
                            <Button size="sm" className="bg-red-600 hover:bg-red-700" onClick={() => { setModalMode('call'); setIsAddModalOpen(true); }}>
                                <Plus className="h-4 w-4 mr-2" /> ADD RECIPIENT
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-red-500/10">
                                        <TableHead className="text-red-500">AUTHORITY / PERSON</TableHead>
                                        <TableHead>CATEGORY</TableHead>
                                        <TableHead>PHONE NUMBER</TableHead>
                                        <TableHead>RETRY STATUS</TableHead>
                                        <TableHead className="text-right">MGMT</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {contacts.call.map((c, i) => (
                                        <TableRow key={i} className="hover:bg-red-500/5">
                                            <TableCell className="font-bold">{c.name}</TableCell>
                                            <TableCell><Badge variant="outline" className="text-[10px] uppercase">{c.category}</Badge></TableCell>
                                            <TableCell className="font-mono text-xs">{c.number}</TableCell>
                                            <TableCell><Badge variant="outline" className="text-emerald-500 border-emerald-500/50">STBY_RETRY_5X</Badge></TableCell>
                                            <TableCell className="text-right">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="text-red-500 hover:bg-red-500/10"
                                                    onClick={() => handleDeleteContact(c.number)}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* ADD CONTACT MODAL */}
            <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
                <DialogContent className="sm:max-w-[425px] bg-[#0c0c0e] border-muted-foreground/10 text-white">
                    <DialogHeader>
                        <DialogTitle className="uppercase font-black text-xl tracking-tighter">Register Emergency Endpoint</DialogTitle>
                        <DialogDescription className="text-xs font-mono uppercase opacity-50">
                            Configure {modalMode.toUpperCase()} notification protocol
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Contact Name</label>
                            <Input value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Fire Deparment" className="bg-muted/50 border-white/5" />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">PH Phone Number</label>
                            <Input value={newNumber} onChange={e => setNewNumber(e.target.value)} placeholder="+639..." className={`bg-muted/50 border-white/5 ${error ? 'border-red-500' : ''}`} />
                            {error && <p className="text-[10px] text-red-500 font-bold uppercase">{error}</p>}
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Hazard Category</label>
                            <select
                                value={newCategory}
                                onChange={e => setNewCategory(e.target.value)}
                                className="w-full bg-muted/50 border border-white/5 rounded-md p-2 text-sm text-white"
                            >
                                <option value="general">GENERAL / ALL</option>
                                <option value="fire">FIRE DEPARTMENT</option>
                                <option value="rain">FLOOD / RAIN MONITOR</option>
                                <option value="smoke">SMOKE / GAS DEPT</option>
                                <option value="debris">STRUCTURAL / DEBRIS</option>
                            </select>
                        </div>
                        {modalMode === 'sms' && (
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Alert Message Body</label>
                                <textarea
                                    value={newMessage}
                                    onChange={e => setNewMessage(e.target.value)}
                                    className="w-full min-h-[80px] bg-muted/50 border border-white/5 rounded-md p-2 text-sm"
                                    placeholder="Enter custom alert text..."
                                />
                            </div>
                        )}
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setIsAddModalOpen(false)} className="text-xs font-bold">CANCEL</Button>
                        <Button onClick={handleAddContact} className={`text-xs font-bold ${modalMode === 'sms' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-red-600 hover:bg-red-700'}`}>
                            SAVE ENDPOINT
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
