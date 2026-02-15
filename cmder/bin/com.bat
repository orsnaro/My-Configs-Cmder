@echo off
if "%~2"=="" (
	set "TITLE=%~1"
	
)

if not "%~2"=="" (
	set "TITLE=%~1"
	set "BODY=%~2"
)

git commit -m "%TITLE%" -m "%BODY%"
set TITLE=
set BODY=
exit /b 0

