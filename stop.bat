@echo off
echo Stopping SignBridge v4...
taskkill /FI "WINDOWTITLE eq SignBridge Backend*"  /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SignBridge Frontend*" /T /F >nul 2>&1
echo Done.
timeout /t 2 /nobreak >nul
