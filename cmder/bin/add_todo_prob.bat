@echo off
rem assign this bat file to an cmder alias  so you can with one command save the new problem you solved and push it to the remote repo 


setlocal
set oldpath=%cd%

rem your code file without the extenstion (write ur code in constant name file e.g. Cp.cpp)
set src_file=Cp

set ext=%1

rem change your repo path here
cd C:\Users\%USERNAME%\repo_CPP_COMP_study\


rem Specify the folder to count the files in. (make it if not present first)
set todoFolder=todo_probs\
if not exist "%todoFolder%" mkdir "%todoFolder%"

rem Get the number of files in the folder.
set /a FILECOUNT=0
for /f %%a in ('dir /b /a-d-s-h "%todoFolder%"') do set /a FILECOUNT+=1


rem change the file that you solve CP in it  ( -1 one for the readme.md that is counted once as a a problem code )
set /a FILECOUNT= %FILECOUNT% - 1
copy %src_file%.%ext%  %todoFolder%prob_no_%FILECOUNT%.%ext%

echo todo problem file: prob_no_%FILECOUNT%.%ext%

rem enter the link of problem to be added to git commit message (optional)
set /p commitMsg=paste problem link:  || set commitMsg=NoLinkProvided

rem add commit then push the new problem in todo folder
git add .\%src_file%.%ext% .\todo_probs & git commit -m "#todo: %commitMsg% #" & git push


cd %oldpath%
endlocal
