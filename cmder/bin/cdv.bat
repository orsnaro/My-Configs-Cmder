@ECHO off
SETLOCAL EnableDelayedExpansion

REM ~ABOUT THE COMMAND~

rem this 'cdv' command soft modifies 'cd' command by doing this:
rem 0. works/tested on windows10 OS. used like this: `cdv path_arg <toggle_venv_arg>`
rem 1.always using /d switch of 'cd' command 
rem 2. check if path you cdv'ing to is a repo dir e.g.( its name starts with repo_ and its and dir not file)
rem 3. if its a dirs and starts with dirt check if there is exist python venv for it : if there is activate it , if not make it then activate it
rem 4. to use it easly add `cdv.bat` folder path to your path variable in system environmental variables

rem [DONE]TODO add extra arg to toggle venv for non-python repoes/proj dirs (if the arg is set then skip making/activating this  and deactivate current venv if cdv'ed to non-python repo/proj dir)

rem !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
rem IMPORTANT: the command mostly used inside aliases of cd to repoes ( other wise make its default to disable extra modification and do normal cd unless %2 is set to "1")
rem !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

REM ~END ABOUT THE COMMAND~


REM ~THE BATCH SCRIPT~


rem NOTE: change it to your project-folder's-name-patterns that you want to make and activate their python venvs AUTO when just cdv to them!
rem all my repos/proj dirs starts with "repo_"
set "targetDirNamePrfxPattern=repo_"
rem assign size of pattern
set "ptrnSz=5"
rem END NOTE

set dquote=^"
set "toCheckPath=%1"
set "toggleVenv= %2"


rem safer to get all strings in double quotes but for our script will take all quotes out
if "!toCheckPath:~0,1!"=="!dquote!" ( set toCheckPath=!toCheckPath:~1,-1! )
rem remove any white spaces
set toCheckPath=!toCheckPath: =!

if defined toggleVenv (
	if "%2"=="1" (
		rem disable all cdv effects only deactivate python venv then  normally change dir via 'cd' to the provided path ( 
		ENDLOCAL
		if defined VIRTUAL_ENV ( call %VIRTUAL_ENV%\Scripts\deactivate )
		goto normal_cd
	) 
)

set "lastChar=%toCheckPath:~-1%"
if not "!lastChar!"=="\" ( set "toCheckPath=!toCheckPath!\" )
if exist "!toCheckPath!" ( 
	rem leaving the backslash at end of path will make it harder to use '~' or get dir name using other methods. so remove it!
	set toCheckPath=!toCheckPath:~0,-1!

	for /d %%p in (!toCheckPath!) do (
		set "dir_name=%%~np" 
		rem actually ~nx gets the name with extention in case of path was file not dir path '~' is extractor or slicing operator must work inside for loop
	)
	
	if "!dir_name:~0,%ptrnSz%!"=="!targetDirNamePrfxPattern!" (
		rem NOTE: <optional> get the name with out the "repo_" part. This is optional step as this would be your venv folder name for this project of repo
		rem choose any name pattern that will not be repeated orr assign same proj folder name to proj venv name...
		
		set  "venv_dir_name=!dir_name:~5!"
		
		rem if super folder for all venvs of project not exist make it then make venv if not there then activate it!
		if not exist "C:\Users\%USERNAME%\py_envs\" ( mkdir C:\Users\%USERNAME%\py_envs\ )
		if not exist "C:\Users\%USERNAME%\py_envs\!venv_dir_name!\" (
			echo NOTE: no python virtual environment found for !dir_name!. 
			echo creating new !dir_name! venv ...
			call C:\Python311\python.exe -m venv C:\Users\%USERNAME%\py_envs\!venv_dir_name!\ 
			echo Done creating new venv. activating ...
		)
		set final_venv_active_path=C:\Users\%USERNAME%\py_envs\!venv_dir_name!\Scripts\activate
		
		rem all this variable will vanish after ENDLOCAL is called so save the path to a file instead to be able to use after ENDLOCAL
		type nul > C:\Users\%USERNAME%\final_venv_active_path.txt
		echo !final_venv_active_path! > C:\Users\%USERNAME%\final_venv_active_path.txt
		
		rem end localisation before running activate.bat so delcared env var inside it remain global scoped
		ENDLOCAL 
		
		set /p final_venv_active_path=<  C:\Users\%USERNAME%\final_venv_active_path.txt
		if defined VIRTUAL_ENV ( call %VIRTUAL_ENV%\Scripts\deactivate )
		call %final_venv_active_path%
		
		
	) else (
		ENDLOCAL
		rem ENDLOCAL
		cd /d %1
		rem cd works after ending localisation  so new dir in %CD% is in global scope not local
		exit /b 0
	)	
) else (
	echo err: provided path Does not Exist!
	ENDLOCAL
	exit /b 3 rem error val: didn't find resources requested
)


if defined VIRTUAL_ENV ( call %VIRTUAL_ENV%\Scripts\deactivate )
call %final_venv_active_path%
rm -f C:\Users\%USERNAME%\final_venv_active_path.txt

:normal_cd
rem finally cd to your project folder and exit :)!

rem ENDLOCAL
cd /d %1
rem cd works after ending localisation  so new dir in %CD% is in global scope not local
exit /b 0

REM ~END THE BATCH SCRIPT~


