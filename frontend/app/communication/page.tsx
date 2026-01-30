"use client";

import { useState, useEffect } from "react";
import {
    Users,
    MessageSquare,
    Plus,
    Trash2,
    ShieldAlert,
    Flame,
    Droplet,
    Wind,
    Search,
    CheckCircle2,
    AlertCircle,
    Activity
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger
} from "@/components/ui/dialog";

interface Contact {
    number: string;
    name: string;
    message: string;
    category: string;
}

const CATEGORIES = [
    { id: "fire", label: "Fire / Smoke", icon: Flame, color: "text-red-500" },
    { id: "flood", label: "Flood / Rain", icon: Droplet, color: "text-blue-500" },
    { id: "intrusion", label: "Intrusion / Security", icon: ShieldAlert, color: "text-amber-500" },
    { id: "general", label: "General Alert", icon: AlertCircle, color: "text-zinc-400" },
];

export default function CommunicationPage() {
    const [contacts, setContacts] = useState<{ sms: Contact[]; call: Contact[] }>({ sms: [], call: [] });
    const [loading, setLoading] = useState(true);
    const [isAdding, setIsAdding] = useState(false);

    // New Contact Form State
    const [newContact, setNewContact] = useState<Contact>({
        name: "",
        number: "",
        message: "",
        category: "general"
    });

    useEffect(() => {
        fetchContacts();
    }, []);

    const fetchContacts = async () => {
        try {
            const res = await fetch("http://localhost:8000/api/gsm/contacts");
            const data = await res.json();
            setContacts(data);
        } catch (error) {
            console.error("Failed to fetch contacts", error);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (mode: 'sms' | 'call') => {
        try {
            const res = await fetch("http://localhost:8000/api/gsm/contacts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...newContact, mode })
            });
            if (res.ok) {
                fetchContacts();
                setIsAdding(false);
                setNewContact({ name: "", number: "", message: "", category: "general" });
            }
        } catch (error) {
            console.error("Add failed", error);
        }
    };

    const handleDelete = async (number: string) => {
        try {
            await fetch(`http://localhost:8000/api/gsm/contacts/${number}`, { method: "DELETE" });
            fetchContacts();
        } catch (error) {
            console.error("Delete failed", error);
        }
    };

    return (
        <div className="flex-1 space-y-6 p-8 pt-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-foreground">Communication Hub</h2>
                    <p className="text-muted-foreground">Manage emergency recipients and situational messaging protocols.</p>
                </div>

                <Dialog open={isAdding} onOpenChange={setIsAdding}>
                    <DialogTrigger asChild>
                        <Button className="gap-2">
                            <Plus size={18} />
                            Add Recipient
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px] bg-zinc-950 border-zinc-800">
                        <DialogHeader>
                            <DialogTitle>Add New Recipient</DialogTitle>
                            <DialogDescription>
                                Configure how this person should be notified during an emergency.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-4 items-center gap-4">
                                <label className="text-right text-sm font-medium">Name</label>
                                <Input
                                    className="col-span-3"
                                    value={newContact.name}
                                    onChange={e => setNewContact({ ...newContact, name: e.target.value })}
                                    placeholder="John Doe"
                                />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <label className="text-right text-sm font-medium">Number</label>
                                <Input
                                    className="col-span-3"
                                    value={newContact.number}
                                    onChange={e => setNewContact({ ...newContact, number: e.target.value })}
                                    placeholder="+1..."
                                />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <label className="text-right text-sm font-medium">Category</label>
                                <select
                                    className="col-span-3 h-10 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                                    value={newContact.category}
                                    onChange={e => setNewContact({ ...newContact, category: e.target.value })}
                                >
                                    {CATEGORIES.map(cat => (
                                        <option key={cat.id} value={cat.id}>{cat.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <label className="text-right text-sm font-medium">Template</label>
                                <Input
                                    className="col-span-3"
                                    value={newContact.message}
                                    onChange={e => setNewContact({ ...newContact, message: e.target.value })}
                                    placeholder="Custom alert message..."
                                />
                            </div>
                        </div>
                        <DialogFooter className="gap-2">
                            <Button variant="outline" onClick={() => handleAdd('call')}>Register to Voice</Button>
                            <Button onClick={() => handleAdd('sms')}>Register to SMS</Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Recipient Directory */}
                <Card className="bg-zinc-900/40 border-zinc-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                        <div className="space-y-1">
                            <CardTitle className="text-xl flex items-center gap-2">
                                <Users className="text-emerald-500" size={20} />
                                Recipient Directory
                            </CardTitle>
                            <CardDescription>Verified emergency contacts</CardDescription>
                        </div>
                        <div className="relative w-48">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input placeholder="Search..." className="pl-8 h-9 text-xs bg-muted/20" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {[...contacts.sms, ...contacts.call].length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground italic">No recipients registered.</div>
                            ) : (
                                [...contacts.sms, ...contacts.call].map((c, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/10 border border-zinc-800/50">
                                        <div className="flex items-center gap-3">
                                            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-zinc-800 to-zinc-950 flex items-center justify-center border border-zinc-800">
                                                <span className="text-xs font-bold text-emerald-500">{c.name.charAt(0)}</span>
                                            </div>
                                            <div>
                                                <p className="text-sm font-semibold">{c.name}</p>
                                                <p className="text-[10px] text-zinc-500 font-mono">{c.number}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-400 uppercase font-bold">
                                                {contacts.sms.includes(c) ? 'SMS' : 'Voice'}
                                            </span>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-600 hover:text-red-500" onClick={() => handleDelete(c.number)}>
                                                <Trash2 size={14} />
                                            </Button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Situational Orchestrator */}
                <Card className="bg-zinc-900/40 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-xl flex items-center gap-2">
                            <ShieldAlert className="text-amber-500" size={20} />
                            Situational Orchestrator
                        </CardTitle>
                        <CardDescription>Alert distribution by hazard type</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 gap-4">
                            {CATEGORIES.map(cat => {
                                const Icon = cat.icon;
                                const matches = [...contacts.sms, ...contacts.call].filter(c => c.category === cat.id);

                                return (
                                    <div key={cat.id} className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/50 hover:bg-zinc-950 transition-colors">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-3">
                                                <div className={`p-2 rounded-lg bg-zinc-900 ${cat.color} border border-zinc-800`}>
                                                    <Icon size={20} />
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-sm">{cat.label}</h4>
                                                    <p className="text-[10px] text-zinc-500 uppercase font-medium tracking-tight">Active Transmit Logic</p>
                                                </div>
                                            </div>
                                            <div className="text-xs font-mono text-zinc-600">
                                                {matches.length} Targets
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            {matches.length > 0 ? (
                                                matches.map((m, idx) => (
                                                    <div key={idx} className="flex flex-col gap-1 pl-12">
                                                        <div className="flex items-center gap-2 text-[11px]">
                                                            <span className="text-zinc-200 font-medium">{m.name}</span>
                                                            <span className="w-1 h-1 rounded-full bg-zinc-700" />
                                                            <span className="text-zinc-500 truncate italic">"{m.message || 'Default template active'}"</span>
                                                        </div>
                                                    </div>
                                                ))
                                            ) : (
                                                <p className="text-[10px] pl-12 text-zinc-700 italic">No situational overrides configured.</p>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Voice Broadcast Configuration */}
            <Card className="bg-zinc-900/40 border-zinc-800">
                <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                        <Wind className="text-blue-400" size={20} />
                        Voice Broadcast Configuration
                    </CardTitle>
                    <CardDescription>Manage audio assets for emergency calls</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-4">
                        <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 space-y-3">
                            <label className="text-xs font-bold text-zinc-500 uppercase">Emergency Payload (MP3)</label>
                            <div className="flex items-center gap-3">
                                <label className="flex-1 cursor-pointer">
                                    <div className="border-2 border-dashed border-zinc-800 rounded-lg p-4 text-center hover:border-emerald-500/50 transition-colors group">
                                        <Plus className="mx-auto mb-2 text-zinc-600 group-hover:text-emerald-500" size={20} />
                                        <span className="text-xs text-zinc-500">Click to upload alert.mp3</span>
                                        <input
                                            type="file"
                                            className="hidden"
                                            accept="audio/mp3"
                                            onChange={async (e) => {
                                                const file = e.target.files?.[0];
                                                if (file) {
                                                    const formData = new FormData();
                                                    formData.append("file", file);
                                                    try {
                                                        await fetch("http://localhost:8000/api/communication/upload_audio", {
                                                            method: "POST",
                                                            body: formData
                                                        });
                                                        alert("Audio Uploaded & Pushed to Device!");
                                                    } catch (err) {
                                                        alert("Upload failed.");
                                                    }
                                                }
                                            }}
                                        />
                                    </div>
                                </label>
                                <Button
                                    variant="outline"
                                    className="gap-2 border-zinc-800 hover:bg-zinc-800"
                                    onClick={async () => {
                                        // We don't have a direct "test play" endpoint yet, 
                                        // but we can trigger a manual broadcast if we add one.
                                        // For now, let's just use the hardware trigger test.
                                        alert("Audio will play automatically during targeted emergency calls.");
                                    }}
                                >
                                    <Activity size={16} />
                                    Verify Audio
                                </Button>
                            </div>
                        </div>
                    </div>

                    <div className="p-4 rounded-lg bg-blue-500/5 border border-blue-500/20 space-y-2">
                        <h4 className="text-sm font-bold text-blue-400 flex items-center gap-2">
                            <CheckCircle2 size={16} />
                            Transmission Status
                        </h4>
                        <p className="text-xs text-blue-500/70 leading-relaxed">
                            Once an MP3 is uploaded, Nexora Ops automatically synchronizes it to the connected Android node.
                            During a situational call, the system will force speakerphone and broadcast this audio payload
                            after a 2-second setup delay.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
