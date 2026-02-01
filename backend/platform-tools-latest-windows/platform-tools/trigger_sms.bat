SET PATH=%PATH%;C:\Windows\System32\OpenSSH
SET PATH=%PATH%;C:\Windows\System32\OpenSSH
SET PATH=%PATH%;C:\Windows\System32\OpenSSH
@echo off
:: --- CONFIGURATION ---
:: Enter the recipient's phone number and password below
SET PHONE=09614806675
SET MSG="Test message 5 - New Console"
SET PASS=5090

echo [1/3] Starting USB Tunnel...
%~dp0adb.exe forward tcp:8022 tcp:8022

echo [2/3] Detecting Phone User...
:: This line automatically grabs the username (u0_aXXX) from the phone
:: Auto-detection replaced by worker
SET USER=u0_a10443

echo [3/3] Sending SMS via %USER%...
:: Using sshpass to inject the password and skipping the 'trust this host' prompt
%~dp0sshpass.exe -v -p %PASS% C:\Windows\System32\OpenSSH\ssh.exe -p 8022 -o StrictHostKeyChecking=no %USER%@127.0.0.1 "termux-sms-send -n %PHONE% %MSG%"

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

exit /b %ERRORLEVEL%
