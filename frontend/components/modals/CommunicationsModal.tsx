"use client"

import { useState } from 'react';
import { Phone, MessageSquare, X, Send } from 'lucide-react';
import { sendSMS, initiateCall } from '@/lib/api';

interface CommunicationsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function CommunicationsModal({ isOpen, onClose }: CommunicationsModalProps) {
    const [activeTab, setActiveTab] = useState<'call' | 'sms'>('call');
    const [number, setNumber] = useState('');
    const [message, setMessage] = useState('');
    const [status, setStatus] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    if (!isOpen) return null;

    const handleAction = async () => {
        if (!number) return;

        setLoading(true);
        setStatus('Processing...');

        // For "Window Testing" (Simulated/PC Mode)
        // We try to use the backend API first (ADB), if that fails/timeouts, we fallback to protocol handlers

        try {
            // Timeout 5s for ADB operation
            const promise = activeTab === 'call'
                ? initiateCall(number)
                : sendSMS(number, message);

            // Race against timeout
            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Timeout')), 5000)
            );

            await Promise.race([promise, timeoutPromise]);

            setStatus('Request Sent via ADB Node');

        } catch (e) {
            console.warn("Backend ADB failed, falling back to local protocol handlers", e);
            // Fallback to PC Protocol Handlers (Phone Link / Skype)
            setStatus('Opening Default App...');
            if (activeTab === 'call') {
                window.open(`tel:${number}`, '_self');
            } else {
                window.open(`sms:${number}?body=${encodeURIComponent(message)}`, '_self');
            }
        }

        setLoading(false);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-950/50">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        Comms Uplink
                    </h2>
                    <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-zinc-800">
                    <button
                        onClick={() => setActiveTab('call')}
                        className={`flex-1 p-4 flex items-center justify-center gap-2 transition-colors ${activeTab === 'call' ? 'bg-zinc-800 text-white border-b-2 border-emerald-500' : 'text-zinc-400 hover:text-zinc-200'
                            }`}
                    >
                        <Phone size={18} />
                        Voice Uplink
                    </button>
                    <button
                        onClick={() => setActiveTab('sms')}
                        className={`flex-1 p-4 flex items-center justify-center gap-2 transition-colors ${activeTab === 'sms' ? 'bg-zinc-800 text-white border-b-2 border-emerald-500' : 'text-zinc-400 hover:text-zinc-200'
                            }`}
                    >
                        <MessageSquare size={18} />
                        Data Stream (SMS)
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-4">

                    <div className="space-y-2">
                        <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Target Endpoint (Number)</label>
                        <input
                            type="tel"
                            placeholder="+1 (555) 000-0000"
                            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-white focus:outline-none focus:border-emerald-500 transition-colors font-mono"
                            value={number}
                            onChange={(e) => setNumber(e.target.value)}
                        />
                    </div>

                    {activeTab === 'sms' && (
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Payload (Message)</label>
                            <textarea
                                placeholder="Enter message..."
                                className="w-full h-32 bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-white focus:outline-none focus:border-emerald-500 transition-colors resize-none"
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                            />
                        </div>
                    )}

                    {status && (
                        <div className="text-xs text-center p-2 rounded bg-zinc-800/50 text-emerald-400">
                            {status}
                        </div>
                    )}

                    <button
                        onClick={handleAction}
                        disabled={loading}
                        className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-4 rounded-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <span className="animate-spin">⏳</span>
                        ) : activeTab === 'call' ? <Phone size={18} /> : <Send size={18} />}

                        {activeTab === 'call' ? 'INITIATE CALL' : 'TRANSMIT DATA'}
                    </button>

                </div>

                <div className="px-6 pb-6 pt-2">
                    <button
                        onClick={async () => {
                            setLoading(true);
                            setStatus('Simulating Sensor Breach...');
                            try {
                                await fetch('http://localhost:8000/api/test/trigger_hardware?alert_level=4');
                                setStatus('Triggered! Broadcasting to Recipients.');
                            } catch (e) {
                                setStatus('Trigger Failed');
                            }
                            setLoading(false);
                            // Clear status after 3s
                            setTimeout(() => setStatus(null), 3000);
                        }}
                        className="w-full text-xs font-bold text-red-400 bg-red-950/20 border border-red-900/50 hover:bg-red-900/40 py-3 rounded transition-colors uppercase tracking-widest mt-6"
                    >
                        ⚠️ Test Hardware Trigger
                    </button>
                </div>
            </div>
        </div>
    );
}
