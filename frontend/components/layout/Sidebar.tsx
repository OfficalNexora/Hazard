"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    Map as MapIcon,
    Radio,
    AlertTriangle,
    Settings,
    Activity,
    Terminal
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Live Map", href: "/map", icon: MapIcon },
    { name: "Cameras", href: "/cameras", icon: (props: any) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" /><circle cx="12" cy="13" r="3" /></svg> },
    { name: "Devices", href: "/devices", icon: Radio },
    { name: "Alerts", href: "/alerts", icon: AlertTriangle },
    { name: "Communication", href: "/communication", icon: Radio },
    { name: "Analysis", href: "/analysis", icon: Activity },
    { name: "Automation", href: "/automation", icon: Terminal },
    { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    // I upgraded this sidebar to be collapsible (Mini Sidebar pattern).
    // It defaults to w-16 (icons only) and expands to w-64 on hover for full text.
    // This maximizes screen real estate for the map/dashboard while keeping navigation accessible.
    return (
        <aside className="hidden md:flex fixed left-0 top-0 z-40 h-screen w-16 hover:w-64 border-r bg-card/50 backdrop-blur-xl transition-all duration-300 group overflow-hidden flex-col">
            <div className="flex h-14 items-center border-b px-3.5 whitespace-nowrap overflow-hidden">
                <Activity className="h-6 w-6 min-w-[24px] text-primary animate-pulse mr-3.5" />
                <span className="text-lg font-bold tracking-wider text-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-100">
                    NEXORA <span className="text-primary">OPS</span>
                </span>
            </div>

            <nav className="space-y-1 p-2 group-hover:p-4 transition-all">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-2.5 py-3 text-sm font-medium transition-all hover:bg-muted whitespace-nowrap overflow-hidden relative",
                                isActive
                                    ? "bg-primary/10 text-primary hover:bg-primary/15"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <Icon className={cn("h-5 w-5 min-w-[20px] shrink-0", isActive && "text-primary")} />
                            <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-75">
                                {item.name}
                            </span>
                        </Link>
                    );
                })}
            </nav>

            <div className="absolute bottom-4 left-0 w-full px-2 group-hover:px-4 transition-all">
                <div className="rounded-lg border bg-card p-2 group-hover:p-4 whitespace-nowrap overflow-hidden transition-all">
                    <div className="flex items-center gap-3">
                        <div className="h-2 w-2 min-w-[8px] rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-semibold text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-100">
                            SYSTEM ONLINE
                        </span>
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-100 pl-5">
                        v2.4.0-stable
                    </p>
                </div>
            </div>
        </aside>
    );
}
