# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['nexus_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\busto\\OneDrive\\Documents\\MOD-EVAC-MS\\backend', 'backend'), ('C:\\Users\\busto\\OneDrive\\Documents\\MOD-EVAC-MS\\frontend/out', 'frontend/out'), ('C:\\Users\\busto\\OneDrive\\Documents\\MOD-EVAC-MS/frontend_public/out', 'frontend_public/out')],
    hiddenimports=['engineio.async_drivers.threading', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan.on', 'win32timezone'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MOD-EVAC-SERVER',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
