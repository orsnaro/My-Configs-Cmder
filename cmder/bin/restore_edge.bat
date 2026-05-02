@echo off
setlocal enabledelayedexpansion

:: 1. Define paths
set "BACKUP_ROOT=D:\EdgeBackups\batch"
set "DEST_DIR=C:\Users\%USERNAME%\AppData\Local\Microsoft\Edge\User Data\Profile 7"
set "LOG_FILE=%BACKUP_ROOT%\restore.log"

:: 2. Check if D: drive/Backup root exists
if not exist "%BACKUP_ROOT%" (
    echo [!] ERROR: Backup folder not found. Is the D: drive connected?
    pause
    exit /b
)

:: 3. Selection Menu / Auto-restore check
if "%~1"=="latest" (
    echo [i] Auto-restore mode triggered. Selecting latest backup...
    set "choice=1"
    goto :SKIP_MENU
)

echo.
echo ===========================================
echo   EDGE RESTORE - SELECT BACKUP VERSION
echo ===========================================
if exist "%BACKUP_ROOT%\profile.1" echo [1] Latest Backup (profile.1)
if exist "%BACKUP_ROOT%\profile.2" echo [2] Previous Backup (profile.2)
if exist "%BACKUP_ROOT%\profile.3" echo [3] Oldest Backup (profile.3)
echo [Q] Quit
echo ===========================================
set /p "choice=Select a version to restore (1/2/3): "

:SKIP_MENU
if "%choice%"=="1" set "SOURCE_DIR=%BACKUP_ROOT%\profile.1"
if "%choice%"=="2" set "SOURCE_DIR=%BACKUP_ROOT%\profile.2"
if "%choice%"=="3" set "SOURCE_DIR=%BACKUP_ROOT%\profile.3"
if /i "%choice%"=="Q" exit /b

if not defined SOURCE_DIR (
    echo Invalid choice.
    pause
    exit /b
)

if not exist "%SOURCE_DIR%" (
    echo [%DATE% %TIME%] ERROR: Selected backup version %choice% not found on D: >> "%LOG_FILE%"
    echo [!] ERROR: Selected backup version does not exist.
    pause
    exit /b
)

:: 4. Kill the Windows Edge process 
echo.
echo Closing Edge to release file locks...
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM MicrosoftEdgeUpdate.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul

:: 4. Restore the data
echo Restoring data from D: edge backup TO C: edge location...
:: /MIR makes the C: drive folder exactly match the D: backup
@REM robocopy "%SOURCE_DIR%" "%DEST_DIR%" /MIR /MT:8 /R:0 /W:0 /XF Cookies* "Safe Browsing Cookies" /LOG+:"%LOG_FILE%" /NP /TEE
robocopy "%SOURCE_DIR%" "%DEST_DIR%" /E /ZB /IS /IT /MT:128 /R:3 /W:3 /LOG+:"%LOG_FILE%" /NP /TEE

echo [%DATE% %TIME%] SUCCESS: Edge Restore from D: Drive COMPLETED. >> "%LOG_FILE%"
echo.
echo Restore Finished. 
pause