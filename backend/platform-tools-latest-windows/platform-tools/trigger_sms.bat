@echo off
:: trigger_sms.bat - DEBUG MODE
cd /d "%~dp0"

echo [DEBUG] Vars:
echo PHONE=%SMS_PHONE%
echo MSG=%SMS_MSG%
echo USER=%SMS_USER%

echo [DEBUG] Port Forwarding...
adb.exe forward tcp:8022 tcp:8022 >nul 2>&1

echo [DEBUG] Sending SMS via %SMS_USER%...
sshpass.exe -v -p %SMS_PASS% ssh -p 8022 -o StrictHostKeyChecking=no %SMS_USER%@127.0.0.1 "termux-sms-send -n %SMS_PHONE% ""%SMS_MSG%"""

exit /b %ERRORLEVEL%
