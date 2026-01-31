@echo off
:: --- CONFIGURATION ---
:: Enter the recipient's phone number and password below
SET PHONE=09614120815
SET MSG="Alert!! FIRE DETECTED !!"
SET PASS=5090

echo [1/3] Starting USB Tunnel...
%~dp0adb.exe forward tcp:8022 tcp:8022

echo [2/3] Detecting Phone User...
:: This line automatically grabs the username (u0_aXXX) from the phone
for /f "tokens=*" %%i in ('%~dp0adb.exe shell whoami') do set USER=%%i

echo [3/3] Sending SMS via %USER%...
:: Using sshpass to inject the password and skipping the 'trust this host' prompt
%~dp0sshpass.exe -p %PASS% ssh -p 8022 -o StrictHostKeyChecking=no %USER%@localhost "termux-sms-send -n %PHONE% %MSG%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Message sent.
) else (
    echo.
    echo FAILED: Check the following:
    echo 1. Is 'sshd' running in Termux?
    echo 2. Is 'sshpass.exe' in the same folder as this script?
    echo 3. Is the password '%PASS%' correct?
)

pause