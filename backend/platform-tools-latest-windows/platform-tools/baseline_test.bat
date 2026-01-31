@echo off
SET PHONE=09614806675
SET MSG="Baseline Test Message"
SET PASS=5090
SET USER=u0_a10443

echo [DEBUG] Testing with hardcoded USER: %USER%
"%~dp0adb.exe" forward tcp:8022 tcp:8022
"%~dp0sshpass.exe" -p %PASS% ssh -p 8022 -o StrictHostKeyChecking=no %USER%@localhost "termux-sms-send -n %PHONE% %MSG%"

echo Error Level was: %ERRORLEVEL%
