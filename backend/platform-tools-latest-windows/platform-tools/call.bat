@echo off
:: --- CONFIGURATION ---
SET PHONE=09092259916
SET PASS=5090
SET MP3_PATH='~/storage/music/fire.mp3'
SET LOCAL_AUDIO=C:\Users\Victo\Downloads\ttsMP3.com_VoiceText_2026-1-30_17-36-43.mp3

echo [1/4] Checking ADB Device...
"%~dp0adb.exe" get-state >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No Android device detected via ADB. 
    echo Please connect your phone, enable USB Debugging, and make sure it is authorized.
    echo.
    pause
    exit /b
)
"%~dp0adb.exe" forward tcp:8022 tcp:8022

echo [2/4] Detecting Termux User...
:: Get UID for com.termux (more reliable than 'whoami' or manual entry)
for /f "tokens=2 delims=:" %%a in ('"%~dp0adb.exe" shell pm list packages -U com.termux') do set UID_RAW=%%a
set UID=%UID_RAW: =%

if "%UID%"=="" (
    echo ERROR: Termux not found on the device.
    pause
    exit /b
)

:: Convert UID to App-User format (e.g., 10443 -> u0_a443)
set /a APP_ID=%UID% %% 100000
set USER=u0_a%APP_ID%
echo Detected User: %USER%

echo [3/4] Playing Local Audio...
:: Use PowerShell to play MP3 on Windows
powershell -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open('%LOCAL_AUDIO%'); $p.Play(); Start-Sleep 5"

echo [4/4] Executing Android Actions...

:: Using sshpass for autotyping the password
set SSH_CMD="%~dp0sshpass.exe" -p %PASS% ssh -p 8022 -o StrictHostKeyChecking=no %USER%@localhost

:: To Make a Call:
%SSH_CMD% "termux-telephony-call %PHONE%"

:: To Play an MP3 on Android:
%SSH_CMD% "termux-media-player play %MP3_PATH%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Commands sent.
) else (
    echo.
    echo FAILED: Check Termux:API permissions, 'sshd' status, and password.
)
pause