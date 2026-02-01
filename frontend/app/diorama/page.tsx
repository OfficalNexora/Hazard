'use client';

/**
 * MOD-EVAC-MS - 3D Digital Twin Page
 * 
 * Full-page interactive 3D visualization of the monitored diorama/building.
 */

import DioramaViewer from '@/components/diorama/DioramaViewer';
import Link from 'next/link';

export default function DioramaPage() {
    return (
        <div className="h-screen w-screen bg-gray-900 flex flex-col">
            {/* Header */}
            <header className="h-14 bg-gray-800/90 border-b border-gray-700 flex items-center px-4 gap-4">
                <Link
                    href="/"
                    className="text-gray-400 hover:text-white transition-colors"
                >
                    ← Back to Dashboard
                </Link>
                <div className="h-6 w-px bg-gray-700" />
                <h1 className="text-lg font-semibold text-white flex items-center gap-2">
                    <span className="text-2xl">🏗️</span>
                    3D Digital Twin
                </h1>
                <div className="flex-1" />
                <div className="text-xs text-gray-500">
                    Scroll to zoom • Drag to rotate • Right-click to pan
                </div>
            </header>

            {/* 3D Viewer */}
            <main className="flex-1 relative">
                <DioramaViewer
                    apiBase={process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                    refreshInterval={1000}
                />
            </main>
        </div>
    );
}
