@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
:: Note: No quotes here, we add them later in the commands
set "SOURCE_DIR=C:\Users\OmarPc\AppData\Local\Microsoft\Edge\User Data\Default"
set "DEST_DIR=D:\EdgeBackups\profile"
set "LOG_FILE=D:\EdgeBackups\sync.log"

:: 2. Ensure D: drive exists
if not exist "D:\" (
    echo [!] ERROR: D: drive not found.
    pause
    exit /b
)

:: 3. Create backup dir if missing
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

:: 4. Kill Edge
echo Closing Edge to release file locks...
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM MicrosoftEdgeUpdate.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul

:: 5. Size Checks
set "HIST_SIZE=0"
set "LOGIN_SIZE=0"

if exist "%SOURCE_DIR%\History" (
    for %%A in ("%SOURCE_DIR%\History") do set "HIST_SIZE=%%~zA"
)
if exist "%SOURCE_DIR%\Login Data" (
    for %%A in ("%SOURCE_DIR%\Login Data") do set "LOGIN_SIZE=%%~zA"
)

echo Detected History: %HIST_SIZE% bytes
echo Detected Logins: %LOGIN_SIZE% bytes

:: Size & File Existense Checks (using 50KB for history and 40KB for login as a threshold for 'empty')
:: 50KB = 51200 | 40KB = 40960
if %HIST_SIZE% GTR 51200 (
    if %LOGIN_SIZE% GTR 40960 (
        echo Data looks healthy. Starting Robocopy...
        
        :: Execute Robocopy
        robocopy "%SOURCE_DIR%" "%DEST_DIR%" /MIR /MT:8 /R:0 /W:0 /XF Cookies* "Safe Browsing Cookies" /XD "Cache" "Code Cache" "GPUCache" /LOG+:"%LOG_FILE%" /NP /TEE
        
        echo %DATE% %TIME%: Edge Backup SUCCESS. >> "%LOG_FILE%"
        goto :FINISHED
    )
)

echo %DATE% %TIME%: WARNING - Data too small. Aborted. >> "%LOG_FILE%"
echo [!] Safety check failed.

:FINISHED
echo Done.