"use client";

import { useEffect, useState } from "react";
import { Bell, Search, ShieldCheck, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function Header() {
    const [time, setTime] = useState("");
    const [notifications, setNotifications] = useState([
        { id: 1, title: "Motion Detected", desc: "Camera 03 (North Gate) trigger", time: "2m ago", unread: true },
        { id: 2, title: "Device Offline", desc: "Sensor-Node-B lost connection", time: "15m ago", unread: true },
        { id: 3, title: "System Update", desc: "Patch v2.4.0 applied successfully", time: "1h ago", unread: false },
    ]);

    const unreadCount = notifications.filter(n => n.unread).length;

    useEffect(() => {
        const updateTime = () => {
            const now = new Date();
            setTime(now.toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }));
        };
        updateTime();
        const interval = setInterval(updateTime, 1000);
        return () => clearInterval(interval);
    }, []);

    const markAllRead = () => {
        setNotifications(notifications.map(n => ({ ...n, unread: false })));
    };

    return (
        <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex flex-1 items-center gap-4">
                <div className="relative w-96">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        type="search"
                        placeholder="Search logs, devices, or alerts..."
                        className="pl-8 bg-muted/50 border-none focus-visible:ring-1"
                    />
                </div>
            </div>

            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5">
                    <ShieldCheck className="h-4 w-4 text-green-500" />
                    <span className="text-xs font-medium text-muted-foreground">SECURE</span>
                </div>

                <div className="font-mono text-sm font-bold text-primary">
                    {time}
                </div>

                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="ghost" size="icon" className="relative">
                            <Bell className="h-5 w-5" />
                            {unreadCount > 0 && (
                                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                            )}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-80 p-0" align="end">
                        <div className="flex items-center justify-between border-b px-4 py-3">
                            <h4 className="font-semibold">Notifications</h4>
                            {unreadCount > 0 && (
                                <Button variant="ghost" size="sm" className="h-auto px-2 text-xs" onClick={markAllRead}>
                                    <Check className="mr-1 h-3 w-3" />
                                    Mark all read
                                </Button>
                            )}
                        </div>
                        <ScrollArea className="h-[300px]">
                            {notifications.length === 0 ? (
                                <div className="p-4 text-center text-sm text-muted-foreground">
                                    No new notifications
                                </div>
                            ) : (
                                <div className="flex flex-col">
                                    {notifications.map((notification) => (
                                        <button
                                            key={notification.id}
                                            className={`flex flex-col items-start gap-1 border-b px-4 py-3 text-left hover:bg-muted/50 transition-colors ${notification.unread ? 'bg-primary/5' : ''}`}
                                        >
                                            <div className="flex w-full items-center justify-between">
                                                <span className={`text-sm font-medium ${notification.unread ? 'text-primary' : 'text-foreground'}`}>
                                                    {notification.title}
                                                </span>
                                                <span className="text-xs text-muted-foreground">{notification.time}</span>
                                            </div>
                                            <p className="text-xs text-muted-foreground line-clamp-2">
                                                {notification.desc}
                                            </p>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </ScrollArea>
                    </PopoverContent>
                </Popover>

                {/* Local Host Indicator - No User Auth */}
                <div className="flex flex-col items-end hidden md:flex">
                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Local Server</span>
                    <code className="text-xs font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">192.168.1.157</code>
                </div>
            </div>
        </header>
    );
}
