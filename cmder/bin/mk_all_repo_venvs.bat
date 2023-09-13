@ECHO off
SETLOCAL
SET oldPath=%cd% 

rem run one time to make python venvs for all your dirs that start with repo_ and activated using cdv instead of cd command

rem Set the current directory as the source directory.
set "sourcedir=c:\Users\%USERNAME%"

rem set your own target token to detect a repo dir
set "target=repo"

rem Iterate through all the subdirectories of the source directory.
for /d %%b in ("%sourcedir%\%target%*") do (
	
	rem DO WHATEVER YOU WANT INSIDE REPO DIR HERE: 

	rem special format for coloring echo output (find full list in cmder/bin/colors.bat)
	echo.
    echo [93m [93m===================================================================[0m
	echo [93m [93m      MSG: Checking venv for  "[96m%%~nxb[93m"      [0m
	echo [93m [93m===================================================================[0m	
	echo.
	
	
	@echo on
	cdv %%b -d
	@echo off
)

echo on
echo %oldPath%
@echo on
cd %home% 
@echo off
CD %home%
ENDLOCAL

