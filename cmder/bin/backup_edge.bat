@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
set "SOURCE_DIR=C:\Users\%USERNAME%\AppData\Local\Microsoft\Edge\User Data\Profile 7"
set "BACKUP_ROOT=D:\EdgeBackups\batch"
set "LOG_FILE=%BACKUP_ROOT%\sync.log"

:: 2. Ensure D: drive exists
if not exist "D:\" (
    echo [!] ERROR: D: drive not found.
    pause
    exit /b
)

:: 3. Create backup root if missing
if not exist "%BACKUP_ROOT%" mkdir "%BACKUP_ROOT%"

:: 4. Kill Edge
echo Closing Edge to release file locks...
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM MicrosoftEdgeUpdate.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul

:: 5. Size Checks
set "HIST_SIZE=0"
set "LOGIN_SIZE=0"
set "BOOKMARKS_SIZE=0"
set "PREFS_SIZE=0"
set "WEBDATA_SIZE=0"

if exist "%SOURCE_DIR%\History" (for %%A in ("%SOURCE_DIR%\History") do set "HIST_SIZE=%%~zA")
if exist "%SOURCE_DIR%\Login Data" (for %%A in ("%SOURCE_DIR%\Login Data") do set "LOGIN_SIZE=%%~zA")
if exist "%SOURCE_DIR%\Bookmarks" (for %%A in ("%SOURCE_DIR%\Bookmarks") do set "BOOKMARKS_SIZE=%%~zA")
if exist "%SOURCE_DIR%\Preferences" (for %%A in ("%SOURCE_DIR%\Preferences") do set "PREFS_SIZE=%%~zA")
if exist "%SOURCE_DIR%\Web Data" (for %%A in ("%SOURCE_DIR%\Web Data") do set "WEBDATA_SIZE=%%~zA")

echo Detected History: %HIST_SIZE% bytes
echo Detected Logins: %LOGIN_SIZE% bytes
echo Detected Bookmarks: %BOOKMARKS_SIZE% bytes
echo Detected Preferences: %PREFS_SIZE% bytes
echo Detected Web Data: %WEBDATA_SIZE% bytes

:: 6. Hard Minimum Size Checks (Absolute safety net)
:: History > 50KB, Login > 40KB, Bookmarks > 10KB, Preferences > 10KB
if %HIST_SIZE% LSS 51200 ( echo [!] History is below absolute minimum. & goto :ABORT_BACKUP )
if %LOGIN_SIZE% LSS 40960 ( echo [!] Login Data is below absolute minimum. & goto :ABORT_BACKUP )
if %BOOKMARKS_SIZE% LSS 10240 ( echo [!] Bookmarks are below absolute minimum. & goto :ABORT_BACKUP )
if %PREFS_SIZE% LSS 10240 ( echo [!] Preferences are below absolute minimum. & goto :ABORT_BACKUP )

:: 7. Delta/Drop Checks (Compare against last successful backup)
set "SIZE_FILE=%BACKUP_ROOT%\last_sizes.txt"
if exist "%SIZE_FILE%" (
    for /f "tokens=1,2 delims==" %%A in (%SIZE_FILE%) do set "LAST_%%A=%%B"

    rem Calculate 80% of last size (allowing a 20% drop)
    rem Note: Batch math is limited to 32-bit integers (~2GB max).
    set /a "MIN_HIST=(!LAST_HIST_SIZE! / 10) * 8" 2>nul
    set /a "MIN_LOGIN=(!LAST_LOGIN_SIZE! / 10) * 8" 2>nul
    set /a "MIN_BM=(!LAST_BOOKMARKS_SIZE! / 10) * 8" 2>nul
    set /a "MIN_PREFS=(!LAST_PREFS_SIZE! / 10) * 8" 2>nul

    if !HIST_SIZE! LSS !MIN_HIST! ( echo [!] History shrank by more than 20%%. & goto :ABORT_BACKUP )
    if !LOGIN_SIZE! LSS !MIN_LOGIN! ( echo [!] Login Data shrank by more than 20%%. & goto :ABORT_BACKUP )
    if !BOOKMARKS_SIZE! LSS !MIN_BM! ( echo [!] Bookmarks shrank by more than 20%%. & goto :ABORT_BACKUP )
    if !PREFS_SIZE! LSS !MIN_PREFS! ( echo [!] Preferences shrank by more than 20%%. & goto :ABORT_BACKUP )
)

echo Data looks healthy. Rotating old backups...

rem 1. Delete oldest backup (3)
if exist "%BACKUP_ROOT%\profile.3" rd /s /q "%BACKUP_ROOT%\profile.3"

rem 2. Shift 2 -> 3
if exist "%BACKUP_ROOT%\profile.2" ren "%BACKUP_ROOT%\profile.2" profile.3

rem 3. Shift 1 -> 2
if exist "%BACKUP_ROOT%\profile.1" ren "%BACKUP_ROOT%\profile.1" profile.2

echo Starting Robocopy to profile.1...
rem Execute Robocopy to profile.1
@REM robocopy "%SOURCE_DIR%" "%BACKUP_ROOT%\profile.1" /MIR /MT:8 /R:0 /W:0 /XF Cookies* "Safe Browsing Cookies" /XD "Cache" "Code Cache" "GPUCache" /LOG+:"%LOG_FILE%" /NP /TEE
robocopy "%SOURCE_DIR%" "%BACKUP_ROOT%\profile.1" /MIR /MT:4 /ZB /R:3 /W:3 /IT /IS
:: Save new sizes for next time
echo HIST_SIZE=%HIST_SIZE%> "%SIZE_FILE%"
echo LOGIN_SIZE=%LOGIN_SIZE%>> "%SIZE_FILE%"
echo BOOKMARKS_SIZE=%BOOKMARKS_SIZE%>> "%SIZE_FILE%"
echo PREFS_SIZE=%PREFS_SIZE%>> "%SIZE_FILE%"

echo %DATE% %TIME%: Edge Backup SUCCESS ^(profile.1^). >> "%LOG_FILE%"
goto :FINISHED

:ABORT_BACKUP
echo %DATE% %TIME%: WARNING - Data check failed (Size Drop Detected). Aborted. >> "%LOG_FILE%"
echo [!] Safety check failed. Possible data loss detected.
echo [i] Initiating automatic restore of the latest backup...
echo.
call "%~dp0restore_edge.bat" latest

:FINISHED
echo Done.