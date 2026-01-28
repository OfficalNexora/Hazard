"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    Map as MapIcon,
    Radio,
    AlertTriangle,
    Settings,
    Activity
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Live Map", href: "/map", icon: MapIcon },
    { name: "Cameras", href: "/cameras", icon: (props: any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" /><circle cx="12" cy="13" r="3" /></svg> },
    { name: "Devices", href: "/devices", icon: Radio },
    { name: "Alerts", href: "/alerts", icon: AlertTriangle },
    { name: "Analysis", href: "/analysis", icon: Activity },
    { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    // I built this sidebar with a fixed position and backdrop blur to maintain visibility over complex map or video backgrounds.
    // The active state logic here ensures the operator always knows their context within the application application.
    return (
        <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card/50 backdrop-blur-xl">
            <div className="flex h-16 items-center border-b px-6">
                <Activity className="mr-2 h-6 w-6 text-primary animate-pulse" />
                <span className="text-lg font-bold tracking-wider text-foreground">
                    NEXORA <span className="text-primary">OPS</span>
                </span>
            </div>

            <nav className="space-y-1 p-4">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all hover:bg-muted",
                                isActive
                                    ? "bg-primary/10 text-primary hover:bg-primary/15"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <Icon className={cn("h-5 w-5", isActive && "text-primary")} />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="absolute bottom-4 left-0 w-full px-4">
                <div className="rounded-lg border bg-card p-4">
                    <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-semibold text-muted-foreground">SYSTEM ONLINE</span>
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground">v2.4.0-stable</p>
                </div>
            </div>
        </aside>
    );
}
