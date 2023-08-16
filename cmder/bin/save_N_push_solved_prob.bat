@echo off
rem assign this bat file to an cmder alias  so you can with one command save the new problem you solved and push it to the remote repo 

setlocal
set oldpath=%cd%

rem change your repo path here
cd C:\Users\%USERNAME%\repo_CPP_COMP_study\


rem Specify the folder to count the files in. (make it if not present first)
set probsFolder=done_probs\

rem Get the number of files in the folder.
set /a FILECOUNT=0
for /f %%a in ('dir /b /a-d-s-h "%probsFolder%"') do set /a FILECOUNT+=1

rem enter the link of problem to be added to git commit message (optional)
set /p commitMsg=paste problem link:  || set commitMsg=NoLinkProvided

rem note: change the file CP.cpp to one that you solve problems in it 
copy CP.cpp  %probsFolder%\prob_no_%FILECOUNT%.cpp

rem add, commit and push your new solved problem in its own file (optional: leave problem url in the commit message)
git add .\CP.cpp .\done_probs\ & git commit -m "#Done: %commitMsg% #" & git push


cd %oldpath%
endlocal