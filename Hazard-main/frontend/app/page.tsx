'use client';

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Droplets, RotateCcw, AlertTriangle, Wifi, WifiOff, Phone, Bell, Box } from "lucide-react";
import { useSensorData, useAlertState, useDetections, useDevices } from "@/lib/hooks";

// Alert state colors and labels
const ALERT_CONFIG: Record<string, { color: string; bgColor: string; label: string }> = {
  SAFE: { color: 'text-emerald-500', bgColor: 'bg-emerald-500/10', label: 'SAFE' },
  CALLING: { color: 'text-amber-500', bgColor: 'bg-amber-500/10', label: 'CALLING' },
  MESSAGING: { color: 'text-blue-500', bgColor: 'bg-blue-500/10', label: 'MESSAGE' },
  DANGER: { color: 'text-red-500', bgColor: 'bg-red-500/10', label: 'DANGER' },
  EVACUATE: { color: 'text-red-600', bgColor: 'bg-red-600/20', label: 'EVACUATE' },
};

// Hazard class colors
const HAZARD_COLORS: Record<string, string> = {
  'Fire': 'bg-red-500',
  'Explosion': 'bg-red-600',
  'Smoke': 'bg-gray-500',
  'Flood': 'bg-blue-500',
  'Landslide': 'bg-orange-500',
  'Falling Debris': 'bg-yellow-500',
  'Collapsed Structure': 'bg-red-800',
  'Industrial Accident': 'bg-purple-500',
};

export default function Dashboard() {
  // I designed this component as the central point of truth for the operator.
  // It aggressively pulls data from multiple hooks (sensors, alerts, detections) to form a complete operational picture.
  const { data: sensorData, connected } = useSensorData();
  const { alert, triggerEvacuation, setSafeMode, loading: alertLoading } = useAlertState();
  const detections = useDetections(10);
  const devices = useDevices();
  const [accessCode, setAccessCode] = useState<string>('--- ---');

  useEffect(() => {
    import('@/lib/api').then(api => {
      api.fetchAccessCode().then(res => setAccessCode(res.code));
    });
  }, []);

  const alertConfig = ALERT_CONFIG[alert.state] || ALERT_CONFIG.SAFE;
  const connectedDevices = devices.filter(d => d.connected).length;
  // Get first active camera for preview
  const activeCamera = devices.find(d => d.connected && (d.device_type === 'esp32_cam' || d.device_id.includes('cam')));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Mission Control</h1>
        <div className="flex items-center gap-4">
          {/* 3D Digital Twin Link */}
          <Link
            href="/diorama"
            className="flex items-center gap-2 px-3 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20 transition-colors"
          >
            <Box className="h-4 w-4 text-cyan-500" />
            <span className="text-sm font-medium text-cyan-500">3D Twin</span>
          </Link>

          {/* Connection Status */}
          <div className="flex items-center gap-2">
            {connected ? (
              <>
                <Wifi className="h-4 w-4 text-emerald-500" />
                <span className="text-sm font-medium text-emerald-500">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium text-muted-foreground">Offline</span>
              </>
            )}
          </div>

          {/* Alert Indicator */}
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${alertConfig.bgColor}`}>
            <span className="flex h-2 w-2 relative">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${alertConfig.color.replace('text-', 'bg-')} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${alertConfig.color.replace('text-', 'bg-')}`}></span>
            </span>
            <span className={`text-sm font-semibold ${alertConfig.color}`}>{alertConfig.label}</span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Raining Monitor (formerly Water Level) */}
        <Card className="border-blue-500/20 bg-blue-500/5">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
            <CardTitle className="text-[10px] font-black text-blue-500 uppercase tracking-widest">RAINING MONITOR</CardTitle>
            <Droplets className={`h-3.5 w-3.5 ${(sensorData?.raining ?? 0) > 70 ? 'text-red-500' :
              (sensorData?.raining ?? 0) > 40 ? 'text-amber-500' : 'text-blue-500'
              }`} />
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <div className={`text-xl font-black ${(sensorData?.raining ?? 0) > 70 ? 'text-red-500' :
              (sensorData?.raining ?? 0) > 40 ? 'text-amber-500' : 'text-blue-500'
              }`}>
              {sensorData?.raining?.toFixed(1) ?? '0.0'}%
            </div>
            <p className="text-[9px] text-blue-500/70 mt-0.5 uppercase tracking-tighter font-mono">Precipitation intensity</p>
          </CardContent>
        </Card>

        {/* Fire Monitor (New) */}
        <Card className={`border-2 ${sensorData?.fire ? 'border-red-600 bg-red-600/20 animate-pulse' : 'border-emerald-500/20 bg-emerald-500/5'}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
            <CardTitle className={`text-[10px] font-black ${sensorData?.fire ? 'text-red-500' : 'text-emerald-500'} uppercase tracking-widest`}>FIRE MONITOR</CardTitle>
            <AlertTriangle className={`h-3.5 w-3.5 ${sensorData?.fire ? 'text-red-500' : 'text-emerald-500'}`} />
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <div className={`text-xl font-black ${sensorData?.fire ? 'text-red-500' : 'text-emerald-500'}`}>
              {sensorData?.fire ? 'CRITICAL' : 'NORMAL'}
            </div>
            <p className={`text-[9px] mt-0.5 uppercase tracking-tighter font-mono ${sensorData?.fire ? 'text-red-400' : 'text-emerald-500/70'}`}>
              {sensorData?.fire ? 'FLAME DETECTED' : 'NO HAZARD'}
            </p>
          </CardContent>
        </Card>

        {/* Earthquake Monitor (formerly Orientation) */}
        <Card className="border-orange-500/20 bg-orange-500/5">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
            <CardTitle className="text-[10px] font-black text-orange-500 uppercase tracking-widest">EARTHQUAKE MONITOR</CardTitle>
            <RotateCcw className="h-3.5 w-3.5 text-orange-500" />
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <div className="font-mono text-[10px] space-y-0.5 text-orange-500/80">
              <div className="flex justify-between">
                <span>LATERAL X:</span>
                <span className="font-bold">{sensorData?.earthquake?.x?.toFixed(2) ?? '0.00'}°</span>
              </div>
              <div className="flex justify-between">
                <span>VERTICAL Y:</span>
                <span className="font-bold">{sensorData?.earthquake?.y?.toFixed(2) ?? '0.00'}°</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Station Metadata (Access Code) */}
        {/* Access Code Card */}
        <Card className="border-cyan-500/20 bg-cyan-500/5">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
            <CardTitle className="text-[10px] font-black text-cyan-500 uppercase tracking-widest">STATION PORTAL</CardTitle>
            <Wifi className="h-3.5 w-3.5 text-cyan-500" />
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <div className="text-xl font-black text-cyan-500 tracking-tight">{accessCode}</div>
            <p className="text-[9px] text-cyan-500/70 mt-0.5 uppercase tracking-tighter font-mono">Citizen access code</p>
          </CardContent>
        </Card>

        {/* Emergency Dashboard */}
        <Card className={`${alertConfig.bgColor} border-dashed border-2 ${alertConfig.color.replace('text-', 'border-')}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
            <CardTitle className="text-[10px] font-black uppercase tracking-widest">STATION STATUS</CardTitle>
            <Activity className={`h-3.5 w-3.5 ${alertConfig.color}`} />
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <div className={`text-xl font-black ${alertConfig.color}`}>{alertConfig.label}</div>
            <div className="flex gap-2 mt-1">
              <button
                onClick={() => setSafeMode()}
                className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30 uppercase tracking-tighter"
              >
                Reset Safe
              </button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Sensor Details & Integrated Preview */}
        <Card className="col-span-4 overflow-hidden">
          <CardHeader className="border-b bg-muted/30 py-2.5 px-4">
            <CardTitle className="text-[10px] font-black flex items-center gap-2 uppercase tracking-[0.2em]">
              <Activity className="h-3.5 w-3.5 text-primary" />
              STATION INTELLIGENCE OVERVIEW
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="grid grid-cols-2 h-full">
              {/* Left: Accelerometer Data */}
              <div className="p-4 space-y-3 border-r">
                <div className="space-y-2">
                  <h4 className="text-[9px] font-black text-muted-foreground uppercase tracking-widest">Accelerometer (m/s²)</h4>
                  <div className="font-mono text-xs space-y-1">
                    <div className="flex justify-between items-center p-1.5 rounded bg-muted/50">
                      <span className="text-muted-foreground">AXIS_X:</span>
                      <span className="text-primary font-bold">{sensorData?.accel?.x?.toFixed(3) ?? '0.000'}</span>
                    </div>
                    <div className="flex justify-between items-center p-1.5 rounded bg-muted/50">
                      <span className="text-muted-foreground">AXIS_Y:</span>
                      <span className="text-primary font-bold">{sensorData?.accel?.y?.toFixed(3) ?? '0.000'}</span>
                    </div>
                    <div className="flex justify-between items-center p-1.5 rounded bg-muted/50">
                      <span className="text-muted-foreground">AXIS_Z:</span>
                      <span className="text-primary font-bold">{sensorData?.accel?.z?.toFixed(3) ?? '9.800'}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-[9px] font-black text-red-500 uppercase tracking-widest">Emergency Override</h4>
                  <div className="grid grid-cols-1 gap-1.5">
                    <button
                      onClick={() => import('@/lib/api').then(api => api.triggerManualAction('call_fire'))}
                      className="w-full flex items-center justify-center py-2 rounded bg-red-600 text-white font-black text-[9px] hover:bg-red-700 transition tracking-tighter"
                    >
                      FIRE RESPONSE
                    </button>
                    <button
                      onClick={() => import('@/lib/api').then(api => api.triggerManualAction('earthquake_alert'))}
                      className="w-full flex items-center justify-center py-2 rounded bg-orange-600 text-white font-black text-[9px] hover:bg-orange-700 transition tracking-tighter"
                    >
                      EARTHQUAKE ALERT
                    </button>
                  </div>
                </div>
              </div>

              {/* Right: Integrated Camera Preview */}
              <div className="bg-black relative group">
                {activeCamera ? (
                  <img
                    src={`http://localhost:8000/api/video_feed?id=${activeCamera.device_id}`}
                    className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition"
                    alt="Main Feed"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground space-y-2">
                    <WifiOff className="h-8 w-8 opacity-20" />
                    <span className="text-[10px] font-mono opacity-50">NO PRIMARY STREAM</span>
                  </div>
                )}
                <div className="absolute top-4 right-4 text-[10px] font-mono text-emerald-500 bg-black/80 px-2 py-1 rounded border border-emerald-500/20 backdrop-blur-sm">
                  LIVE_INT_FEED
                </div>
                <div className="absolute bottom-4 left-4 right-4">
                  <button
                    onClick={() => triggerEvacuation()}
                    className="w-full py-2 bg-red-600/90 text-white font-bold text-[10px] rounded backdrop-blur-md hover:bg-red-600 transition tracking-widest uppercase"
                  >
                    System-Wide Evacuation
                  </button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Logs */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle className="text-sm font-bold tracking-widest uppercase">Intelligence Log</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {detections.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4 opacity-30">
                  <Activity className="h-12 w-12" />
                  <p className="text-xs font-mono uppercase tracking-widest text-center">
                    Awaiting Inference...
                  </p>
                </div>
              ) : (
                detections.map((d, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/40 transition group">
                    <span className={`w-3 h-3 rounded-full shrink-0 shadow-sm ${HAZARD_COLORS[d.class] || 'bg-gray-400'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-center">
                        <p className="text-sm font-black uppercase tracking-tight">{d.class}</p>
                        <span className="text-[10px] text-muted-foreground font-mono">#{d.frame_id}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${HAZARD_COLORS[d.class] || 'bg-primary'}`} style={{ width: `${d.confidence * 100}%` }} />
                        </div>
                        <p className="text-[10px] text-muted-foreground font-mono w-8 text-right">
                          {(d.confidence * 100).toFixed(0)}%
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
