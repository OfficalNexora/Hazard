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

export function MobileNav() {
    const pathname = usePathname();

    return (
        <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 h-16 border-t bg-card/80 backdrop-blur-xl px-2 pb-safe">
            <nav className="flex h-full items-center justify-around">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex flex-col items-center justify-center gap-0.5 rounded-lg p-2 transition-colors",
                                isActive
                                    ? "text-primary"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <Icon className={cn("h-5 w-5", isActive && "text-primary")} />
                            <span className="text-[9px] font-medium">{item.name}</span>
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
}
