@echo off
if "%~2"=="" (
    echo Usage: com ^<title^> ^<body^>
    exit /b 1
)

set "TITLE=%~1"
set "BODY=%~2"


git commit -m "%TITLE%" -m "%BODY%"