@echo off
rem assign this bat file to an cmder alias  so you can with one command save the new problem you solved and push it to the remote repo 


setlocal
set oldpath=%cd%

rem change your repo path here
cd C:\Users\%USERNAME%\repo_CPP_COMP_study\


rem Specify the folder to count the files in. (make it if not present first)
set todoFolder=todo_probs\

rem Get the number of files in the folder.
set /a FILECOUNT=0
for /f %%a in ('dir /b /a-d-s-h "%todoFolder%"') do set /a FILECOUNT+=1


rem enter the link of problem to be added to git commit message (optional)
set /p commitMsg=paste problem link:  || set commitMsg=NoLinkProvided

rem change the file that you solve CP in it 
copy CP.cpp  %todoFolder%\prob_no_%FILECOUNT%.cpp

rem add commit then push the new problem in todo folder
git add .\CP.cpp .\todo_probs\ & git commit -m "#todo: %commitMsg% #" & git push


cd %oldpath%
endlocal