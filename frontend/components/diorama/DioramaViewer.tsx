'use client';

/**
 * MOD-EVAC-MS - 3D Diorama Viewer
 * 
 * Interactive Three.js visualization of the monitored environment.
 * Features:
 * - Real-time hazard overlay (red zones)
 * - LED state visualization
 * - Event replay timeline
 * - Camera calibration mode
 */

import React, { useRef, useState, useEffect, useMemo, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Box, Plane, Line } from '@react-three/drei';
import * as THREE from 'three';

// Types matching backend diorama_model.py
interface LEDZone {
    id: number;
    name: string;
    floor: number;
    position: [number, number, number];
    radius: number;
    led_indices: number[];
    danger_on_fire: boolean;
    danger_on_flood: boolean;
    danger_on_seismic: boolean;
    is_exit: boolean;
}

interface Building {
    id: string;
    name: string;
    floors: number;
    bounds: [number, number, number, number, number, number];
    zones: LEDZone[];
}

interface DioramaModel {
    name: string;
    bounds: [number, number, number, number, number, number];
    buildings: Building[];
    exits: LEDZone[];
    zone_connections: Record<number, number[]>;
}

interface HazardEvent {
    id: number;
    timestamp: number;
    event_type: string;
    position: { x: number; y: number; z: number };
    zone_id: number | null;
    zone_name: string | null;
    confidence: number;
}

interface DioramaViewerProps {
    apiBase?: string;
    refreshInterval?: number;
}

// Zone mesh component
function ZoneMesh({
    zone,
    isHazard,
    isOnPath,
    scale = 1
}: {
    zone: LEDZone;
    isHazard: boolean;
    isOnPath: boolean;
    scale: number;
}) {
    const meshRef = useRef<THREE.Mesh>(null);
    const [hovered, setHovered] = useState(false);

    // Pulse animation for hazard zones
    useFrame((state) => {
        if (meshRef.current && isHazard) {
            const pulse = Math.sin(state.clock.elapsedTime * 4) * 0.2 + 0.8;
            meshRef.current.scale.setScalar(pulse);
        } else if (meshRef.current) {
            meshRef.current.scale.setScalar(1);
        }
    });

    // Calculate color based on state
    const color = useMemo(() => {
        if (isHazard) return '#ff3333';
        if (zone.is_exit) return '#00ff00';
        if (isOnPath) return '#44ff44';
        return '#4488ff';
    }, [isHazard, zone.is_exit, isOnPath]);

    const [x, y, z] = zone.position;

    return (
        <group position={[x * scale, z * scale, y * scale]}>
            <mesh
                ref={meshRef}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
            >
                <sphereGeometry args={[zone.radius * scale * 0.5, 16, 16]} />
                <meshStandardMaterial
                    color={hovered ? '#ffffff' : color}
                    transparent
                    opacity={isHazard ? 0.8 : 0.5}
                    emissive={isHazard ? '#ff0000' : '#000000'}
                    emissiveIntensity={isHazard ? 0.5 : 0}
                />
            </mesh>
            {hovered && (
                <Text
                    position={[0, zone.radius * scale * 0.8, 0]}
                    fontSize={0.02 * scale}
                    color="white"
                    anchorX="center"
                    anchorY="bottom"
                >
                    {zone.name}
                </Text>
            )}
        </group>
    );
}

// Building mesh component
function BuildingMesh({
    building,
    scale = 1
}: {
    building: Building;
    scale: number;
}) {
    const [minX, minY, minZ, maxX, maxY, maxZ] = building.bounds;

    const width = (maxX - minX) * scale;
    const depth = (maxY - minY) * scale;
    const height = (maxZ - minZ) * scale;

    const centerX = ((minX + maxX) / 2) * scale;
    const centerY = ((minY + maxY) / 2) * scale;
    const centerZ = ((minZ + maxZ) / 2) * scale;

    return (
        <group>
            {/* Building wireframe */}
            <mesh position={[centerX, centerZ, centerY]}>
                <boxGeometry args={[width, height, depth]} />
                <meshStandardMaterial
                    color="#2a4a6a"
                    transparent
                    opacity={0.15}
                    wireframe={false}
                />
            </mesh>

            {/* Building edges */}
            <lineSegments position={[centerX, centerZ, centerY]}>
                <edgesGeometry args={[new THREE.BoxGeometry(width, height, depth)]} />
                <lineBasicMaterial color="#4a8aca" />
            </lineSegments>

            {/* Floor lines */}
            {Array.from({ length: building.floors + 1 }).map((_, i) => {
                const floorY = (minZ + (i * (maxZ - minZ) / building.floors)) * scale;
                return (
                    <mesh
                        key={i}
                        position={[centerX, floorY, centerY]}
                        rotation={[-Math.PI / 2, 0, 0]}
                    >
                        <planeGeometry args={[width * 0.95, depth * 0.95]} />
                        <meshStandardMaterial
                            color="#3a5a7a"
                            transparent
                            opacity={0.1}
                            side={THREE.DoubleSide}
                        />
                    </mesh>
                );
            })}

            {/* Building label */}
            <Text
                position={[centerX, (maxZ * scale) + 0.05, centerY]}
                fontSize={0.03 * scale * 10}
                color="#88aacc"
                anchorX="center"
                anchorY="bottom"
            >
                {building.name}
            </Text>
        </group>
    );
}

// Connection lines between zones
function ConnectionLines({
    zones,
    connections,
    scale = 1
}: {
    zones: LEDZone[];
    connections: Record<number, number[]>;
    scale: number;
}) {
    const zoneMap = useMemo(() => {
        const map: Record<number, LEDZone> = {};
        zones.forEach(z => { map[z.id] = z; });
        return map;
    }, [zones]);

    const lines = useMemo(() => {
        const result: Array<{ from: number; to: number; points: THREE.Vector3[] }> = [];
        const drawn = new Set<string>();

        Object.entries(connections).forEach(([fromId, toIds]) => {
            const from = parseInt(fromId);
            toIds.forEach(to => {
                const key = [Math.min(from, to), Math.max(from, to)].join('-');
                if (!drawn.has(key) && zoneMap[from] && zoneMap[to]) {
                    drawn.add(key);
                    const p1 = zoneMap[from].position;
                    const p2 = zoneMap[to].position;
                    result.push({
                        from,
                        to,
                        points: [
                            new THREE.Vector3(p1[0] * scale, p1[2] * scale, p1[1] * scale),
                            new THREE.Vector3(p2[0] * scale, p2[2] * scale, p2[1] * scale)
                        ]
                    });
                }
            });
        });

        return result;
    }, [connections, zoneMap, scale]);

    return (
        <>
            {lines.map((line, i) => (
                <Line
                    key={i}
                    points={line.points}
                    color="#446688"
                    lineWidth={1}
                    dashed
                    dashSize={0.02}
                    gapSize={0.01}
                />
            ))}
        </>
    );
}

// Ground plane
function Ground({ bounds, scale = 1 }: { bounds: [number, number, number, number, number, number]; scale: number }) {
    const [minX, minY, , maxX, maxY] = bounds;
    const width = (maxX - minX) * scale;
    const depth = (maxY - minY) * scale;
    const centerX = ((minX + maxX) / 2) * scale;
    const centerY = ((minY + maxY) / 2) * scale;

    return (
        <mesh
            position={[centerX, -0.01, centerY]}
            rotation={[-Math.PI / 2, 0, 0]}
            receiveShadow
        >
            <planeGeometry args={[width * 1.5, depth * 1.5, 20, 20]} />
            <meshStandardMaterial
                color="#1a2a3a"
                wireframe
                transparent
                opacity={0.3}
            />
        </mesh>
    );
}

// Main 3D Scene
function Scene({
    model,
    hazardZones,
    pathZones,
    scale = 100
}: {
    model: DioramaModel | null;
    hazardZones: Set<number>;
    pathZones: Set<number>;
    scale: number;
}) {
    if (!model) {
        return (
            <Text position={[0, 0, 0]} fontSize={0.1} color="white">
                Loading model...
            </Text>
        );
    }

    // Collect all zones
    const allZones = useMemo(() => {
        const zones: LEDZone[] = [...model.exits];
        model.buildings.forEach(b => zones.push(...b.zones));
        return zones;
    }, [model]);

    return (
        <>
            {/* Lighting */}
            <ambientLight intensity={0.4} />
            <directionalLight position={[5, 10, 5]} intensity={0.8} castShadow />
            <pointLight position={[0, 5, 0]} intensity={0.5} color="#4488ff" />

            {/* Ground */}
            <Ground bounds={model.bounds} scale={scale} />

            {/* Buildings */}
            {model.buildings.map(building => (
                <BuildingMesh key={building.id} building={building} scale={scale} />
            ))}

            {/* Connection lines */}
            <ConnectionLines
                zones={allZones}
                connections={model.zone_connections}
                scale={scale}
            />

            {/* Zones */}
            {allZones.map(zone => (
                <ZoneMesh
                    key={zone.id}
                    zone={zone}
                    isHazard={hazardZones.has(zone.id)}
                    isOnPath={pathZones.has(zone.id)}
                    scale={scale}
                />
            ))}

            {/* Camera controls */}
            <OrbitControls
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minDistance={0.5}
                maxDistance={20}
            />
        </>
    );
}

// Timeline component
function Timeline({
    events,
    currentTime,
    onTimeChange
}: {
    events: HazardEvent[];
    currentTime: number;
    onTimeChange: (time: number) => void;
}) {
    if (events.length === 0) return null;

    const minTime = events[0]?.timestamp || 0;
    const maxTime = events[events.length - 1]?.timestamp || Date.now() / 1000;
    const range = maxTime - minTime || 1;

    return (
        <div className="absolute bottom-4 left-4 right-4 bg-gray-900/80 rounded-lg p-3 backdrop-blur">
            <div className="flex items-center gap-4">
                <span className="text-xs text-gray-400">Replay</span>
                <input
                    type="range"
                    min={minTime}
                    max={maxTime}
                    step={1}
                    value={currentTime}
                    onChange={(e) => onTimeChange(parseFloat(e.target.value))}
                    className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
                <span className="text-xs text-gray-400 font-mono">
                    {new Date(currentTime * 1000).toLocaleTimeString()}
                </span>
            </div>
            {/* Event markers */}
            <div className="relative h-2 mt-2">
                {events.map((event, i) => {
                    const pos = ((event.timestamp - minTime) / range) * 100;
                    const color = event.event_type === 'fire' ? 'bg-red-500' :
                        event.event_type === 'flood' ? 'bg-blue-500' :
                            'bg-yellow-500';
                    return (
                        <div
                            key={i}
                            className={`absolute w-1 h-2 ${color} rounded`}
                            style={{ left: `${pos}%` }}
                            title={`${event.event_type} at ${event.zone_name || 'unknown'}`}
                        />
                    );
                })}
            </div>
        </div>
    );
}

// Main component
export default function DioramaViewer({
    apiBase = 'http://localhost:8000',
    refreshInterval = 1000
}: DioramaViewerProps) {
    const [model, setModel] = useState<DioramaModel | null>(null);
    const [events, setEvents] = useState<HazardEvent[]>([]);
    const [hazardZones, setHazardZones] = useState<Set<number>>(new Set());
    const [pathZones, setPathZones] = useState<Set<number>>(new Set());
    const [replayTime, setReplayTime] = useState<number>(Date.now() / 1000);
    const [isReplayMode, setIsReplayMode] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch model on mount
    useEffect(() => {
        async function fetchModel() {
            try {
                const res = await fetch(`${apiBase}/api/diorama/model`);
                if (!res.ok) throw new Error('Failed to load model');
                const data = await res.json();
                setModel(data);
                setLoading(false);
            } catch (e) {
                setError(e instanceof Error ? e.message : 'Unknown error');
                setLoading(false);
            }
        }
        fetchModel();
    }, [apiBase]);

    // Fetch active hazards periodically
    useEffect(() => {
        if (isReplayMode) return;

        async function fetchHazards() {
            try {
                const res = await fetch(`${apiBase}/api/events/active`);
                if (!res.ok) return;
                const data = await res.json();

                const zones = new Set<number>();
                data.hazards?.forEach((h: HazardEvent) => {
                    if (h.zone_id !== null) zones.add(h.zone_id);
                });
                setHazardZones(zones);

                // Also fetch LED commands for path
                const ledRes = await fetch(`${apiBase}/api/pathfinding/led_commands`);
                if (ledRes.ok) {
                    const ledData = await ledRes.json();
                    setPathZones(new Set(ledData.path || []));
                }
            } catch (e) {
                // Silent fail for polling
            }
        }

        fetchHazards();
        const interval = setInterval(fetchHazards, refreshInterval);
        return () => clearInterval(interval);
    }, [apiBase, refreshInterval, isReplayMode]);

    // Fetch events for replay
    useEffect(() => {
        async function fetchEvents() {
            try {
                const now = Date.now() / 1000;
                const hourAgo = now - 3600;
                const res = await fetch(`${apiBase}/api/events?start=${hourAgo}&end=${now}&limit=500`);
                if (!res.ok) return;
                const data = await res.json();
                setEvents(data.events || []);
            } catch (e) {
                // Silent fail
            }
        }
        fetchEvents();
    }, [apiBase]);

    // Handle replay time changes
    useEffect(() => {
        if (!isReplayMode || events.length === 0) return;

        // Find events active at replay time
        const activeEvents = events.filter(e =>
            e.timestamp <= replayTime && e.timestamp > replayTime - 30
        );

        const zones = new Set<number>();
        activeEvents.forEach(e => {
            if (e.zone_id !== null) zones.add(e.zone_id);
        });
        setHazardZones(zones);
    }, [replayTime, events, isReplayMode]);

    if (loading) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-gray-900">
                <div className="text-white">Loading 3D Model...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-gray-900">
                <div className="text-red-400">Error: {error}</div>
            </div>
        );
    }

    return (
        <div className="relative w-full h-full bg-gray-900">
            {/* 3D Canvas */}
            <Canvas
                camera={{ position: [2, 2, 2], fov: 60 }}
                shadows
                gl={{ antialias: true }}
            >
                <color attach="background" args={['#0a1520']} />
                <fog attach="fog" args={['#0a1520', 5, 20]} />

                <Suspense fallback={null}>
                    <Scene
                        model={model}
                        hazardZones={hazardZones}
                        pathZones={pathZones}
                        scale={100}
                    />
                </Suspense>
            </Canvas>

            {/* Controls overlay */}
            <div className="absolute top-4 left-4 flex gap-2">
                <button
                    onClick={() => setIsReplayMode(!isReplayMode)}
                    className={`px-3 py-1 rounded text-sm ${isReplayMode
                        ? 'bg-yellow-600 text-white'
                        : 'bg-gray-700 text-gray-300'
                        }`}
                >
                    {isReplayMode ? '⏸ Live Mode' : '⏪ Replay Mode'}
                </button>
            </div>

            {/* Stats overlay */}
            <div className="absolute top-4 right-4 bg-gray-900/80 rounded-lg p-3 backdrop-blur">
                <div className="text-xs text-gray-400 space-y-1">
                    <div>Hazards: <span className="text-red-400">{hazardZones.size}</span></div>
                    <div>Safe Path: <span className="text-green-400">{pathZones.size} zones</span></div>
                    <div>Events: <span className="text-blue-400">{events.length}</span></div>
                </div>
            </div>

            {/* Legend */}
            <div className="absolute bottom-20 right-4 bg-gray-900/80 rounded-lg p-3 backdrop-blur">
                <div className="text-xs space-y-1">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500" />
                        <span className="text-gray-300">Hazard Zone</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-500" />
                        <span className="text-gray-300">Exit</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-400" />
                        <span className="text-gray-300">Safe Path</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-blue-500" />
                        <span className="text-gray-300">Zone</span>
                    </div>
                </div>
            </div>

            {/* Timeline (replay mode only) */}
            {isReplayMode && (
                <Timeline
                    events={events}
                    currentTime={replayTime}
                    onTimeChange={setReplayTime}
                />
            )}
        </div>
    );
}
