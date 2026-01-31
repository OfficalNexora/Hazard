@echo off
SET PHONE=09614806675
SET MSG="Debug Message from Antigravity"
SET PASS=5090

echo [1/3] Starting USB Tunnel...
"%~dp0adb.exe" forward tcp:8022 tcp:8022

echo [2/3] Detecting Phone User...
for /f "tokens=2 delims=:" %%a in ('"%~dp0adb.exe" shell pm list packages -U com.termux') do set UID_RAW=%%a
set UID=%UID_RAW: =%
set /a APP_ID=%UID% %% 100000
set USER=u0_a%APP_ID%
echo Detected User: %USER%

echo [3/3] Sending SMS via %USER%...
"%~dp0sshpass.exe" -p %PASS% ssh -p 8022 -o StrictHostKeyChecking=no %USER%@localhost "termux-sms-send -n %PHONE% %MSG%"

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Message sent.
) else (
    echo FAILED with Error Level: %ERRORLEVEL%
)
