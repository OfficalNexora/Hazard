"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Loader2, Navigation } from "lucide-react";

// Fix for Leaflet default icons in Next.js
const iconUrl = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png";
const iconRetinaUrl = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png";
const shadowUrl = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png";

const DefaultIcon = L.icon({
    iconUrl,
    iconRetinaUrl,
    shadowUrl,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

// Custom Pulse Icon for User Location
const pulseIcon = L.divIcon({
    className: "relative flex h-4 w-4",
    html: `<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
         <span class="relative inline-flex rounded-full h-4 w-4 bg-blue-500 border-2 border-white"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
});

import { useDevices, useDetections } from "@/lib/hooks";

// Hazard Icon
const hazardIcon = L.divIcon({
    className: "relative flex h-6 w-6",
    html: `<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
         <span class="relative inline-flex rounded-full h-6 w-6 bg-red-600 border-2 border-white flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
         </span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
});

// Device Icon
const deviceIcon = L.divIcon({
    className: "relative flex h-5 w-5",
    html: `<span class="relative inline-flex rounded-full h-5 w-5 bg-emerald-500 border-2 border-white flex items-center justify-center shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/></svg>
         </span>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
});

function MapController({ center }: { center: [number, number] }) {
    const map = useMap();
    useEffect(() => {
        map.flyTo(center, map.getZoom());
    }, [center, map]);
    return null;
}

export default function LiveMap() {
    const [position, setPosition] = useState<[number, number] | null>(null);
    const [accuracy, setAccuracy] = useState<number>(0);
    const [error, setError] = useState<string | null>(null);
    const [weather, setWeather] = useState<any>(null);

    const devices = useDevices();
    const detections = useDetections(10);

    // Geolocation tracking
    useEffect(() => {
        if (!navigator.geolocation) {
            setError("Geolocation not supported");
            return;
        }

        const watchId = navigator.geolocation.watchPosition(
            (pos) => {
                setPosition([pos.coords.latitude, pos.coords.longitude]);
                setAccuracy(pos.coords.accuracy);
                setError(null);
            },
            (err) => {
                setError(err.message);
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );

        return () => navigator.geolocation.clearWatch(watchId);
    }, []);

    // Fetch weather when position is found
    useEffect(() => {
        if (position) {
            import("@/lib/api").then(api => {
                api.fetchWeather(position[0], position[1]).then(data => {
                    setWeather(data);
                }).catch(e => console.error("Weather map fetch failed", e));
            });
        }
    }, [position]);

    if (error) {
        return (
            <div className="flex h-full w-full items-center justify-center bg-card text-destructive">
                <div className="text-center">
                    <Navigation className="mx-auto h-12 w-12 opacity-50 mb-4" />
                    <h3 className="text-lg font-bold">GPS Signal Lost</h3>
                    <p className="text-sm">{error}</p>
                </div>
            </div>
        );
    }

    if (!position) {
        return (
            <div className="flex h-full w-full items-center justify-center bg-muted/20">
                <div className="flex flex-col items-center gap-2">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="text-sm font-medium text-muted-foreground">Triangulating Position...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="relative h-full w-full">
            <MapContainer
                center={position}
                zoom={16}
                scrollWheelZoom={true}
                className="h-full w-full rounded-xl border border-border shadow-sm z-0"
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                />

                {/* Base Station */}
                <Marker position={position} icon={pulseIcon}>
                    <Popup>
                        <div className="text-center">
                            <strong className="block text-primary">MONITORING STATION</strong>
                            <span className="text-xs text-muted-foreground">Main Control Unit</span>
                            {weather && (
                                <div className="mt-2 pt-2 border-t border-dashed">
                                    <div className="flex items-center gap-1 justify-center">
                                        <span className="text-lg font-bold">{weather.current.temperature_2m}°C</span>
                                    </div>
                                    <span className="text-[10px] text-muted-foreground">
                                        Wind: {weather.current.wind_speed_10m} km/h
                                    </span>
                                </div>
                            )}
                        </div>
                    </Popup>
                </Marker>

                {/* Connected Devices (Simulated Position for Demo) */}
                {devices.filter(d => d.connected).map((device, i) => (
                    <Marker
                        key={device.device_id}
                        position={[position[0] + 0.001 * (i + 1), position[1] + 0.001 * (i % 2 === 0 ? 1 : -1)]}
                        icon={deviceIcon}
                    >
                        <Popup>
                            <div className="text-xs">
                                <strong className="block text-emerald-500">{device.device_id.toUpperCase()}</strong>
                                <span>Type: {device.device_type}</span><br />
                                <span>Port: {device.port}</span>
                            </div>
                        </Popup>
                    </Marker>
                ))}

                {/* Hazards (Simulated around station) */}
                {detections.slice(0, 5).map((det, i) => (
                    <Marker
                        key={`det-${i}`}
                        position={[position[0] + 0.0005 * (i + 2), position[1] + 0.0008 * (i % 3 === 0 ? -1 : 1)]}
                        icon={hazardIcon}
                    >
                        <Popup>
                            <div className="text-xs">
                                <strong className="block text-red-500">HAZARD: {det.class.toUpperCase()}</strong>
                                <span>Confidence: {(det.confidence * 100).toFixed(1)}%</span><br />
                                <span>Timestamp: {new Date().toLocaleTimeString()}</span>
                            </div>
                        </Popup>
                    </Marker>
                ))}

                <MapController center={position} />
            </MapContainer>

            {/* Weather Overlay Widget */}
            {weather && (
                <div className="absolute top-4 right-4 z-[400] bg-black/80 backdrop-blur-md border border-white/10 rounded-lg p-3 shadow-2xl animate-in slide-in-from-right-10">
                    <div className="flex items-center gap-3">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">Local Weather</span>
                            <div className="flex items-baseline gap-1">
                                <span className="text-2xl font-bold text-white">{weather.current.temperature_2m}°</span>
                                <span className="text-xs text-muted-foreground">C</span>
                            </div>
                        </div>
                        {/* Simple Icon based on conditions */}
                        <div className="h-8 w-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                            {weather.current.rain > 0 ? (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                                </svg>
                            ) : (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                                </svg>
                            )}
                        </div>
                    </div>
                    {weather.warnings.length > 0 && (
                        <div className="mt-2 text-[9px] text-red-400 font-bold border-t border-white/5 pt-1 uppercase">
                            ! {weather.warnings[0].message}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
