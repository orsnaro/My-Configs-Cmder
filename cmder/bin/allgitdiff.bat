@ECHO off
SETLOCAL  

SET oldPath=%cd%

rem Set the current directory as the source directory.
set "sourcedir=c:\Users\%USERNAME%"

rem set your own target token to detect a repo dir
set "target=repo"

rem Iterate through all the subdirectories of the source directory.
for /d %%b in ("%sourcedir%\%target%*") do (   
	rem DO WHATEVER YOU WANT INSIDE REPO DIR HERE: 
	
	rem special format for coloring echo output (find full list in cmder/bin/colors.bat)
	echo.
    echo [93m [93m==================================================================================[0m
	echo [93m [93m=      Remote [96mRepo[93m [91m^<-[93mDifference Between[91m-^>[93m Local "[96m%%~nxb[93m"[0m 
	echo [93m [93m==================================================================================[0m	
	echo.
	
	cd %%b 
	git diff 
)

CD %oldPath%
ENDLOCAL