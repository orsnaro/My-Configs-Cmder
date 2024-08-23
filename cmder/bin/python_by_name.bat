ECHO OFF

rem  it starts a python script but changes the process name in tskmgr
rem this makes it easier to know which running python script is which

 if defined VIRTUAL_ENV (
	 set  PYTHON_HOME=%VIRTUAL_ENV%\Scripts\
 ) else (
	 if exist %cd%\python.exe (
	          set PYTHON_HOME=%cd%\
	 ) else ( 
	          set PYTHON_HOME=C:\Python311\
         )
 )
 set PYTHON_NAME=%1.exe
 copy "%PYTHON_HOME%python.exe" "%PYTHON_HOME%%PYTHON_NAME%"
 set args=%*
 set args=%args:* =%
 "%PYTHON_HOME%%PYTHON_NAME%" %args%


if "%PYTHON_NAME%" NEQ "python.exe" (
            del "%PYTHON_HOME%%PYTHON_NAME%" 
)
