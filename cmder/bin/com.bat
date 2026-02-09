@echo off
if "%~2"=="" (
	set "TITLE=%~1"
    git commit -m "%TITLE%"
	exit /b 0
)

set "TITLE=%~1"
set "BODY=%~2"

git commit -m "%TITLE%" -m "%BODY%"
exit /b 0

