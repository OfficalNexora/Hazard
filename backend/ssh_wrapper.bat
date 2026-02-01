@echo off
set CMD=%*
%CMD% > out.txt 2>&1
echo DONE %ERRORLEVEL% > status.txt
