'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Navigation, ShieldAlert, Radio } from 'lucide-react';
import { usePublicState } from '@/lib/hooks';

// Fix Leaflet icons
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

// Custom Icons
const stationIcon = L.divIcon({
    className: "relative flex h-6 w-6",
    html: `<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
         <span class="relative inline-flex rounded-full h-6 w-6 bg-blue-600 border-2 border-white flex items-center justify-center">
            <div class="w-3 h-3 bg-white rounded-full"></div>
         </span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
});

const hazardIcon = L.divIcon({
    className: "relative flex h-8 w-8",
    html: `<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
         <span class="relative inline-flex rounded-full h-8 w-8 bg-red-600 border-2 border-white shadow-lg flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
         </span>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
});

function MapController({ center }: { center: [number, number] }) {
    const map = useMap();
    useEffect(() => {
        map.panTo(center);
    }, [center, map]);
    return null;
}

export default function PublicMap() {
    const { state } = usePublicState();
    const [stationPos, setStationPos] = useState<[number, number]>([14.5995, 120.9842]); // Default to Manila for demo

    // Simulate station position around user for demo if GPS is available
    useEffect(() => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition((pos) => {
                setStationPos([pos.coords.latitude, pos.coords.longitude]);
            });
        }
    }, []);

    const detections = state?.detections || [];

    return (
        <MapContainer
            center={stationPos}
            zoom={16}
            className="h-full w-full z-0"
            zoomControl={false}
        >
            <TileLayer
                attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {/* Main Station */}
            <Marker position={stationPos} icon={stationIcon}>
                <Popup>
                    <div className="text-sm font-bold text-blue-500">NEXORA STATION ALPHA</div>
                    <div className="text-xs text-zinc-500">Safe Perimeter: 500m</div>
                </Popup>
            </Marker>

            {/* Detections / Hazards */}
            {detections.slice(0, 5).map((det, i) => (
                <Marker
                    key={i}
                    position={[
                        stationPos[0] + 0.0005 * (i + 1),
                        stationPos[1] + 0.0008 * (i % 2 === 0 ? 1 : -1)
                    ]}
                    icon={hazardIcon}
                >
                    <Popup>
                        <div className="text-sm font-bold text-red-500">HAZARD: {det.class.toUpperCase()}</div>
                        <div className="text-xs text-zinc-500">Sector Clearances Required</div>
                    </Popup>
                </Marker>
            ))}

            <MapController center={stationPos} />
        </MapContainer>
    );
}
