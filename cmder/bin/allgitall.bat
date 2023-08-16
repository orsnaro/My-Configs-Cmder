@ECHO off
SETLOCAL 

SET oldPath=%cd% 

rem Set the current directory as the source directory.
set "sourcedir=c:\Users\%USERNAME%"

rem set your own target token to detect a repo dir
set "target=repo" 

set /p commitMsg=Enter global commit message: || set commitMsg=THIS COMMIT DONE VIA GLOBAL COMMIT and PUSH COMMAND allgitall 

rem Iterate through all the subdirectories of the source directory.
for /d %%b in ("%sourcedir%\%target%*") do (
	rem DO WHATEVER YOU WANT INSIDE REPO DIR HERE: 
	
	rem special format for coloring echo output (find full list in cmder/bin/colors.bat)
	echo.
    echo [93m [93m==================================================================================[0m
	echo [93m [93m= MSG: adding commiting pushing ALL from "[96m%%~nxb[93m" to remote..
	echo [93m [93m==================================================================================[0m	
	echo.
	
	cd %%b
	git add --all && git commit -m "# %commitMsg% #" && git push	
)

CD %oldPath% 
ENDLOCAL  