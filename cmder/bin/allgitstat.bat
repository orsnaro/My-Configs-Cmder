@ECHO off
SETLOCAL

SET oldPath=%cd% 

rem Set the current directory as the source directory.
set "sourcedir=c:\Users\%USERNAME%"

rem set your own target token to detect a repo dir
if [%1] == [] ( 
	set "target=repo" 
) else (
	if "%1" == "-h" ( 
		echo.
		echo [93m [93m==============================================================================[0m
		echo [93m =                    [96m      ~ABOUT THE "allgitstat" COMMAND~                  [93m= [0m
		echo [93m [93m==============================================================================[0m	
		echo [93m version : V0.1.1
		echo [93m Date    : 22-10-2023
		echo [93m made by : orsnaro - Omar Rashad
		echo [93m system  : win10 - cmd 
		
		echo [96m 0. [0m "To get `allgitstat` command help [THIS]  use `allgitstat -h`"
		echo [96m 1. [0m "just type `allgitstat` in CMD to use the tool and check all your repoes status"
		echo [96m 2. [0m "The tool simply loops on all your repo folder and checks using `git status`"
		echo             "if there is any untracked/uncommite/commited but not pushed  files" 
		echo [96m 3. [0m "To set your target repositories folder prefix use `allgitstat <repo_prefix>`"
		echo [96m 4. [0m "By default the prefix is 'repo' so any file named repo will be included" 
		echo             "(all prject file must start with same prefix in order for this tool to work)" 
		echo [96m 4. [0m "All repo folders are assumed to be inside 'c:\Users\%USERNAME%' change it if needed" 
		echo "change projects parent dir via `allgitstat -1 <your_projects_parent_path>`" if no path provided will use current dir
		echo "if first arg is not `-1` will change bot the prefix and parent dir also"
		
		ENDLOCAL
		exit /b 0
	) else ( 
		if "%1" == "-1" ( 
			if [%2] == [] (
				set "sourcedir=%CD%"
			) else (
				set "sourcedir=%2"
			)
			
		) else (
			set "target=%1"
			if [%2] NEQ [] set "sourcedir=%2"
		)
	)
)


REM remove last '\' if there is one
set "lastChar=%sourcedir:~-1%"
if "%lastChar%"=="\" ( set "sourcedir=%sourcedir:~0,-1%" )

rem Iterate through all the subdirectories of the source directory.
for /d %%b in ("%sourcedir%\%target%*") do (
	rem DO WHATEVER YOU WANT INSIDE REPO DIR HERE: 

	rem special format for coloring echo output (find full list in cmder/bin/colors.bat)
	echo.
    echo [93m [93m===================================================================[0m
	echo [93m [93m=    MSG: Getting "[96m%%~nxb[93m" status..[0m
	echo [93m [93m===================================================================[0m	
	echo.
	
	cd %%b 
	git status 
	echo ---------------------------------------- 
	call commited_not_pushed.bat
)

CD %oldPath%
ENDLOCAL
