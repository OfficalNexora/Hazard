@echo off
C:\Users\Victo\Hazard\backend\platform-tools-latest-windows\platform-tools\sshpass.exe -p 5090 ssh -p 8022 -o StrictHostKeyChecking=no u0_a10443@localhost "termux-sms-send -n 09614806675 'Verification from Batch'"
echo DONE %ERRORLEVEL%
