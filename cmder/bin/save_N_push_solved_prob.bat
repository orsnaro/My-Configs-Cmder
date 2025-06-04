@echo off
rem assign this bat file to an cmder alias  so you can with one command save the new problem you solved and push it to the remote repo 
rem commands example: save_N_push_solved_prob.bat cpp   (this could be aliased for shorter command)

setlocal
set oldpath=%cd%

rem your code file without the extenstion (solve in constant name file e.g. Cp.cpp)
set src_file=Cp

set ext=%1

rem change your repo path here
cd C:\Users\%USERNAME%\repo_CPP_COMP_study\


rem Specify the folder to count the files in. (makes it if not present first)
set probsFolder=done_probs\
if not exist "%probsFolder%" mkdir "%probsFolder%"


rem Get the number of files in the folder.
set /a FILECOUNT=0
for /f %%a in ('dir /b /a-d-s-h "%probsFolder%"') do set /a FILECOUNT+=1


rem note: change the file CP.cpp to one that you solve problems in it 
copy %src_file%.%ext%  %probsFolder%prob_no_%FILECOUNT%.%ext%
echo solution file: prob_no_%FILECOUNT%.%ext%

rem enter the link of problem to be added to git commit message (optional)
set /p commitMsg=paste problem link: || set commitMsg=NoLinkProvided

rem add, commit and push your new solved problem in its own file (optional: leave problem url in the commit message)
git add .\Cp.%ext% .\%probsFolder%\ & git commit -m "#Done: %commitMsg% #" & git push


cd %oldpath%
endlocal
