"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    CloudRain,
    Thermometer,
    Wind,
    AlertTriangle,
    MapPin,
    RefreshCcw,
    Sun,
    Cloud
} from "lucide-react";
import { fetchWeather } from "@/lib/api";
import { ForecastChart } from "@/components/weather/ForecastChart";

export default function WeatherPage() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadWeather = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await fetchWeather();
            setData(result);
        } catch (e) {
            setError("Failed to load weather data. Ensure backend is running.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadWeather();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[50vh]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
                <AlertTriangle className="h-12 w-12 text-red-500" />
                <p className="text-muted-foreground">{error || "No data available"}</p>
                <Button onClick={loadWeather} variant="outline">Retry</Button>
            </div>
        );
    }

    const { current, warnings, location } = data;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
                        Weather Intelligence
                        {warnings.length > 0 && (
                            <Badge variant="destructive" className="animate-pulse">
                                {warnings.length} CRITICAL WARNING{warnings.length > 1 ? 'S' : ''}
                            </Badge>
                        )}
                    </h1>
                    <p className="text-muted-foreground flex items-center gap-2 mt-1">
                        <MapPin className="w-3 h-3" />
                        Region: {location.lat.toFixed(2)}, {location.lon.toFixed(2)}
                    </p>
                </div>
                <Button variant="ghost" size="icon" onClick={loadWeather}>
                    <RefreshCcw className="h-4 w-4" />
                </Button>
            </div>

            {/* CRITICAL WARNINGS */}
            {warnings.length > 0 && (
                <div className="grid gap-4">
                    {warnings.map((w: any, i: number) => (
                        <Card key={i} className="bg-red-500/10 border-red-500/50 p-6 flex items-start gap-4 animate-in slide-in-from-top-2">
                            <div className="p-3 bg-red-500/20 rounded-full">
                                <AlertTriangle className="h-6 w-6 text-red-500" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-red-400 mb-1">{w.message}</h3>
                                <p className="text-red-300/80 text-sm">
                                    Immediate action may be required. Monitoring systems are active.
                                </p>
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            {/* CURRENT CONDITIONS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* Temperature */}
                <Card className={`p-6 border-white/5 bg-black/40 ${current.temperature_2m > 35 ? 'border-orange-500/50' : ''}`}>
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium text-muted-foreground">Temperature</span>
                        <Thermometer className={`h-4 w-4 ${current.temperature_2m > 35 ? 'text-orange-500' : 'text-blue-500'}`} />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-4xl font-bold tracking-tighter">
                            {current.temperature_2m}°C
                        </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                        {current.temperature_2m > 35 ? "Dangerous Heat Levels" : "Normal thermal range"}
                    </p>
                </Card>

                {/* Rain */}
                <Card className={`p-6 border-white/5 bg-black/40 ${current.rain > 5 ? 'border-blue-500/50' : ''}`}>
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium text-muted-foreground">Precipitation</span>
                        <CloudRain className="h-4 w-4 text-blue-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-4xl font-bold tracking-tighter">
                            {current.rain}
                        </span>
                        <span className="text-sm text-muted-foreground">mm/h</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                        {current.rain > 5 ? "Heavy Rainfall Detected" : "No significant precipitation"}
                    </p>
                </Card>

                {/* Wind */}
                <Card className={`p-6 border-white/5 bg-black/40 ${current.wind_speed_10m > 40 ? 'border-zinc-500/50' : ''}`}>
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium text-muted-foreground">Wind Speed</span>
                        <Wind className="h-4 w-4 text-zinc-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-4xl font-bold tracking-tighter">
                            {current.wind_speed_10m}
                        </span>
                        <span className="text-sm text-muted-foreground">km/h</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                        {current.wind_speed_10m > 40 ? "Gale Force Winds" : "Calm conditions"}
                    </p>
                </Card>
            </div>

            <Card className="p-6 border-white/5 bg-black/20">
                <div className="flex items-center gap-2 mb-4">
                    <Cloud className="w-5 h-5 text-muted-foreground" />
                    <h3 className="font-semibold">AI Analysis</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                    Weather data is being cross-referenced with local sensor arrays.
                    If forecast thresholds are exceeded, the system will automatically
                    trigger Alert Level 2 (Caution) or Alert Level 3 (Warning) via the control worker.
                </p>
            </Card>
        </div>
    );
}
