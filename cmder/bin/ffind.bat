@echo off

setlocal EnableDelayedExpansion
set oldpath=%cd%

set "toFind=%1"
set "strtMsg=Started Searching in Drive"
set "endMsg=Done Searching in Drive"
set "alphabet=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  
for /L %%a in (0,1,25) do (

	 rem retrieve letter : it expands alphabet variable using '!' 
	 rem then uses slicing operator '~' to slice (start,size) -> (%%a, 1) 
	 rem this gets only one char at crnt index of for loop!
	set crntDrive=!alphabet:~%%a,1!

	if exist !crntDrive!: (
		
		cd /d !crntDrive!:
	
		echo.
		echo [93m [93m===================================================================[0m
		echo [93m [93m=                   [91m%strtMsg%[96m'!crntDrive!'[93m                 =[0m        
		echo [93m [93m===================================================================[0m	
		echo.
		
		dir "\*%toFind%" /a /s
		
		echo.
		echo [93m [93m===================================================================[0m
		echo [93m [93m=                  [92m%endMsg%[96m'!crntDrive!'[93m                     =[0m   
		echo [93m [93m===================================================================[0m	
		echo.
		
	)
	
	
)

cd /d %oldpath%
endlocal