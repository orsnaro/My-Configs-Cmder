@echo off
:: helloacm.com
:: chr function implementation using pure windows batch
 
:: define characters from 32 to 126
set alphabet= !"#$%%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
 
:: set error code for invalid inputs
set errorlevel=0
 
:: valid range should be from 32 to 126 inclusive
if "%1"=="" goto :EOF
if %1 LSS 32 goto :EOF
if %1 GTR 126 goto :EOF
 
:: call function
call :ASCII %1 chr
 
:: print result, using ^ to escape special characters 
:: such as <, > and |
echo.^%chr%
 
:: set error code on success
set errorlevel=%1
 
:: end the script
goto :EOF
 
:: sub-routine
:ASCII
    setlocal EnableDelayedExpansion
        :: get the index
        set /a var=%1-32
        :: retrieve letter
        set character=!alphabet:~%var%,1!
    :: end the routine and return result as second parameter (out)
    endlocal & set %2=^%character%