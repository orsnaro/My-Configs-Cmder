@echo off
setlocal enabledelayedexpansion

:: 1. Define paths (Text only, no internal quotes)
set "SOURCE_DIR=D:\EdgeBackups\profile"
set "DEST_DIR=C:\Users\%USERNAME%\AppData\Local\Microsoft\Edge\User Data\Default"
set "LOG_FILE=D:\EdgeBackups\restore.log"

:: 2. Check if D: drive/Backup folder exists
if not exist "%SOURCE_DIR%" (
    echo [%DATE% %TIME%] ERROR: Backup folder not found on D: >> "%LOG_FILE%"
    echo [!] ERROR: Backup folder not found. Is the D: drive connected?
    pause
    exit /b
)

:: 3. Kill the Windows Edge process 
echo Closing Edge to release file locks...
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM MicrosoftEdgeUpdate.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul

:: 4. Restore the data
echo Restoring data from D: edge backup TO C: edge location...
:: /MIR makes the C: drive folder exactly match the D: backup
robocopy "%SOURCE_DIR%" "%DEST_DIR%" /MIR /MT:8 /R:0 /W:0 /XF Cookies* "Safe Browsing Cookies" /LOG+:"%LOG_FILE%" /NP /TEE

echo [%DATE% %TIME%] SUCCESS: Edge Restore from D: Drive COMPLETED. >> "%LOG_FILE%"
echo.
echo Restore Finished. 
pause