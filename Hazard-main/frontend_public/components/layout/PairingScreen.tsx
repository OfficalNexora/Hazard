'use client';

import { useState } from 'react';
import { KeyRound, ShieldAlert, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PairingScreenProps {
    onPair: (code: string) => Promise<boolean>;
}

export default function PairingScreen({ onPair }: PairingScreenProps) {
    const [code, setCode] = useState(['', '', '', '', '', '']);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleChange = (index: number, value: string) => {
        if (!/^\d*$/.test(value)) return;
        const newCode = [...code];
        newCode[index] = value.slice(-1);
        setCode(newCode);

        // Auto-focus next input
        if (value && index < 5) {
            const nextInput = document.getElementById(`code-${index + 1}`);
            nextInput?.focus();
        }
    };

    const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
        if (e.key === 'Backspace' && !code[index] && index > 0) {
            const nextInput = document.getElementById(`code-${index - 1}`);
            nextInput?.focus();
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const fullCode = code.join('');
        if (fullCode.length !== 6) return;

        setLoading(true);
        setError(null);
        const success = await onPair(fullCode);
        if (!success) {
            setError('Invalid Access Code. Please check with an administrator.');
            setCode(['', '', '', '', '', '']);
            document.getElementById('code-0')?.focus();
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-zinc-950 p-6">
            <div className="w-full max-w-md space-y-8 animate-in fade-in zoom-in duration-500">
                <div className="text-center space-y-2">
                    <div className="mx-auto w-16 h-16 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center mb-4">
                        <KeyRound className="w-8 h-8 text-blue-400" />
                    </div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-white">NEXORA PUBLIC</h1>
                    <p className="text-zinc-400 text-sm">Emergency Evacuation & Hazard Portal</p>
                </div>

                <form onSubmit={handleSubmit} className="bg-zinc-900/50 border border-white/5 p-8 rounded-3xl shadow-2xl backdrop-blur-xl space-y-6">
                    <div className="space-y-4">
                        <label className="text-xs font-semibold uppercase tracking-widest text-zinc-500 text-center block">
                            Enter 6-Digit Station Pairing Code
                        </label>
                        <div className="flex justify-between gap-2">
                            {code.map((digit, i) => (
                                <input
                                    key={i}
                                    id={`code-${i}`}
                                    type="text"
                                    maxLength={1}
                                    value={digit}
                                    onChange={(e) => handleChange(i, e.target.value)}
                                    onKeyDown={(e) => handleKeyDown(i, e)}
                                    disabled={loading}
                                    className={cn(
                                        "w-12 h-16 text-center text-2xl font-bold bg-zinc-800/50 border-2 rounded-xl transition-all outline-none",
                                        error ? "border-red-500/50 text-red-400" : "border-white/10 text-white focus:border-blue-500 focus:bg-blue-500/5"
                                    )}
                                    autoFocus={i === 0}
                                />
                            ))}
                        </div>
                    </div>

                    {error && (
                        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-400/10 p-3 rounded-lg border border-red-400/20 animate-in slide-in-from-top-2">
                            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                            <p>{error}</p>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading || code.some(d => !d)}
                        className="w-full h-12 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'ACCESS PORTAL'}
                    </button>

                    <p className="text-[10px] text-zinc-600 text-center leading-relaxed">
                        Pairing ensures you are connected to the correct local monitoring station.
                        Once paired, your device will receive live safety updates.
                    </p>
                </form>
            </div>
        </div>
    );
}
