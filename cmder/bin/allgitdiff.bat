@ECHO off
SETLOCAL EnableDelayedExpansion

SET oldPath=%cd%

rem Set the current directory as the source directory.
set "sourcedir=c:\Users\%USERNAME%"

rem if there is extra repoes other than your personal one (append them with 'others' if you want them to be tracked)
	set "extra=others"

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

rem check if there is extra repoes other than persons (maybe ones he collabs in)
set /a extra_cnt=0
for /d %%b in ("%sourcedir%\%extra%*") do (
	set /a extra_cnt=!extra_cnt! + 1
)

if !extra_cnt! NEQ 0 (
	echo. 
	echo [44m [44m NOTE: [0m
	echo.
	set /p do_check_extra="repoes you possibly not the owner FOUND* Check Them? [y]es [n]o :  " 
	echo !do_check_extra!
	rem clear any whitespaces
	set do_check_extra=!do_check_extra: =!

	rem get only first char to check if Y,y or n,N
	set firstchar=!do_check_extra:~0,1!
	
	if "!firstChar!" NEQ "y" (
		if "!firstChar!" NEQ "Y" (
			GOTO :exitOk
		)
	)

	REM if got here means yes he wants to check the extra repoes script found!
	
	rem extra 'others' repoes loop: Iterate through all the subdirectories of the source directory.
	echo.
	echo [44m [44m STARTING OTHER LOCAL REPOES STATUS CHECK  [0m
	echo.

	for /d %%b in ("%sourcedir%\%extra%*") do (
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
)


:exitOK
		echo.
		echo "[42m [42m DONE! GETTING DIFF OF ALL LOCAL REPOES <(^^_^^)> [0m"
		echo.


CD %oldPath%
ENDLOCAL
