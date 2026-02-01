"use client";

import { Card } from "@/components/ui/card";

interface ForecastChartProps {
    hourly: {
        time: string[];
        temperature_2m: number[];
        rain: number[];
    };
}

export function ForecastChart({ hourly }: ForecastChartProps) {
    // Take next 24 hours
    const hours = hourly.time.slice(0, 24);
    const temps = hourly.temperature_2m.slice(0, 24);

    // Calculate scale
    const maxTemp = Math.max(...temps, 30);
    const minTemp = Math.min(...temps, 20);
    const range = maxTemp - minTemp;

    return (
        <Card className="p-6 bg-black/40 border-white/5 overflow-x-auto">
            <h3 className="text-sm font-medium mb-4 text-muted-foreground uppercase tracking-widest">24-Hour Temperature Prediction</h3>
            <div className="flex items-end gap-2 h-32 w-max min-w-full pb-2">
                {hours.map((t, i) => {
                    const temp = temps[i];
                    // Normalize height between 20% and 100%
                    const height = ((temp - minTemp) / (range || 1)) * 80 + 20;

                    const date = new Date(t);
                    const label = date.getHours() + ":00";

                    // Color coding for heat
                    let barColor = "bg-blue-500/50";
                    if (temp > 30) barColor = "bg-yellow-500/50";
                    if (temp > 35) barColor = "bg-red-500/80";

                    return (
                        <div key={i} className="flex flex-col items-center gap-1 group relative">
                            <div
                                className={`w-8 rounded-t-sm transition-all group-hover:bg-opacity-100 ${barColor}`}
                                style={{ height: `${height}%` }}
                            >
                                <div className="hidden group-hover:block absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] px-1 py-0.5 rounded whitespace-nowrap">
                                    {temp}°C
                                </div>
                            </div>
                            <span className="text-[10px] text-muted-foreground rotate-0">{label}</span>
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}
