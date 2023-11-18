@echo off 
setlocal

rem .bat to show only not pushed commits of current checked branch i.e.(commited locally but not pushed to remote repo)
rem this is done by : getting crnt branch name and save it to  a tmpFile  , 
rem then read the tmpFile to a tmpVar then use git cmd that shows commited but not pushed commits
rem finally assign .bat to an doskey or alias named `loccom`  i.e.'local commits'
rem why dont redirect name of crnt branch directly to tmpVar? ans: I can but command will be not readable
rem why not using git command directly? ans: this git command by default shows not puhsed commits of master not the current branch 

rem get crnt branch name and save it in tmpFile
git rev-parse --abbrev-ref HEAD> tmpFile

rem save current branch name in temp variable
set /p crntBrnch=< tmpFile

rem run final command to get unpushed commits (git log <since>..<until>) 
 git log origin/%crntBrnch%..HEAD > tmpFile2
 
echo [105m [105m Searching For not Pushed Commits...[0m
 
rem if output of command saved in temp file is empty then we're clear
rem else print the unpushed commits to console
set /p is_clear=< tmpFile2
for /f %%i in ("tmpFile2") do set size=%%~zi
if %size% EQU 0 (echo Clear! no unpushed commits) else ( git log origin/%crntBrnch%..HEAD )

 


rem clean
del /F tmpFile2
del /F tmpFile
set crntBrnch=

endlocal