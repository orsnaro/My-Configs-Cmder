

(F10 to toggle notepad++ bar)

# ###############VS code#############IMPORTANT only
ctr+ shift+ p (all shortcuts vs code)
(NOT DEFAULT) `+4  ( collapse all folders in explorer )
(NOT DEFAULT) shift + ctrl + alt + f (fetch or one mouse button using xmouse)
(NOT DEFAULT)shift + ctrl + alt + c (commit all to local or one mouse button using xmouse)
(NOT DEFAULT)shift + p (push all to remote)
(NOT DEFAULT)shift + p (push all to remote)
(NOT DEFAULT) ~ + Q (toggle side activity bar))
(NOT DEFAULT)ctrl + j/k/l/i (move cursor a word 'instead of arrows')
(NOT DEFAULT)ctrl + alt + j/l (select word lift or right)
(NOT DEFAULT) Alt + T (toggle whitespaces render) 

ctrl + k + release + o (separate vs code in totally diff windows)
ctrl+ tab   (switch between "active" tabs)
alt + left/right (navigate between active tabs)
ctrl+b (close side bar )
win+`  (close terminal side)
ctrl + g (go to line X)
ctrl + 0 ( go outside bracket)


shift+ctrl+/ (jmp to matching bracket)
shift + d    (delete line)
ctrl + /     (comment lines)
shift + alt + up/down   (duplicate selected lines)
SHIFT + K (edit highlighted)
ctrl + space (suggestions)
(NOT DEFAULT) win+F5  (to use vscode debugger <build>)
(NOT DEFAULT) win+F6   ( to use vscode debugger <run>)
(NOT DEFAULT) ` + Q ( to toggle side bar "activity bar")
(NOT DEFAULT) ` + R ( change editor mode " text or hex... etc")
(NOT DEFAULT) ` + 1 (toggle minimap)


ctrl + alt + N (to build and run  using code runner in terminal <no debugging> )


--> for more  https://code.visualstudio.com/shortcuts/keyboard-shortcuts-windows.pdf



# ############### (Cmder + bash + CMD + powershell) ############# IMPORTANT only




cmd 
--> to run/nest new cmd inside cmder/cmd/powershell ( not cmder alias is windows default argument)

ps
-->(NOT DEFAULT)(cmder alias)  to run powershell inside the current cmd/cmder/powershell and nest them 

set 
--> to echo all windaws deafult arguments and variables  

code
--> opens vs code

code .
--> open all current dir on vs code as current workspace

ctrl +c   OR   q
----> terminate current operation

$t
----> seperate mutliple commands in alias

 $b
 --> used when making alias that has '|' pipe char in it  replace the pipe wiht $back
 (also $t is used to to multiple commands in alias, replaces '&&' or ';'  )


$*
---> get all parameters in alias  ( u can get only one parameter $1)
-->OR u can use up to 10 parameters in terminl from $1 to $9
--> SOME TERMINALS CAN ACCEPT MORE USING ${NUM OF PARAMS}

--> more special chars for cmder alias : https://stackoverflow.com/a/59397138


command | clip   OR clip < filename.txt
--->   copy terminal o\p or any .txt to the clipboard

CHDIR /d  drive: path
--> (to change to another partion or drive)

start filename.exe (
--> (open any exe in directory)

ctrl + r 
--> reverse search command histroy ( if ur wanted command is before found one just PRESS ctr + r again until u found it )
ctrl + s
--> forward search in cmder

arrow right
--> get the found search to terminal
 
 
winget list 
--> list all installed programs versions and if there is newer available version for upgrade

winget upgrade --all 
--> update all programs installed 

dir  "\*part_of_filename*"  /s
--> searches for ur file (for linux and cmder u can use 'find' also try find --help)
-->The backslash tells dir to search from the root directory of the current drive.
--> to search for a dir not a file use:
 dir "\*part_of_dir_name*" /AD /S 
--> /A- Displays files with specified attributes. D-May the attribute be Directories

xxd filename.extention 
--> to memory view the file in hexadecimal dump (for bash only + cmder)
xxd filename.extention | vim - 
--> same as previous put to open it inside vim


starz github-username
--> to install 'npm install -g starz' . it's an CMD tool that shows total gihub account stars

 tasklist | grep *your running process name*
 --> this will only search and echo the runing tasks that has same name if there is any
 --> (user defined alias for tasklist command is 'tsk' or 'task'
 
 taskkill /im runing_task_name 
--> kill task using image name (omit /im to kill task by process number PID) 

python -m venv virtual_env_name
--> make new python virtual env 

vritual_env_path/Scripts/activate
--> start your virtual env

deactivate
--> go back to master env (windows)


*Pan manipulation
(WIN TERMINAL PREVIEW)  alt + shift + d/s 
--> duplicate pane ( split horz / vertically ) (ctrl instead of alt to duplicate whole tab not good in quake mode)

(WIN TERMINAL PREVIEW)  alt + right /lift / up / down
--> change focaus between pans

*Tab manipulation
win + shift + left / right :   ( cycles you app tab through monitors)
Ctrl + T : New tab dialog (maybe you want to open cmd as admin?)
Ctrl + W : Close tab
Ctrl + D : Close tab (if pressed on empty command)
Shift + Alt + #Number : Fast new tab: 1 - CMD, 2 - PowerShell
Ctrl + Tab : Switch to next tab
Ctrl + Shift + Tab : Switch to previous tab
Ctrl + #Number : Switch to tab #Number
Alt + Enter: Fullscreen

*Shell  
Ctrl + Alt + U : Traverse up in directory structure (lovely feature!)
End, Home, Ctrl : Traversing text with as usual on Windows
Ctrl + R : History search
Shift + Mouse : Select and copy text from buffer


# ############### (Git) ############# IMPORTANT only

https://kbroman.org/github_tutorial/pages/first_time.html
--> connect and auth git with github acc for push 

create-shortcut "source path" "destination path"
--> create a shortcut (must apend destination path with "ShortcutName.lnk")

git checkout   "hash or branch name"
--> move head (ure current snapshot) to older snapshot of ur dir 
--> or move head to another local branch

git fetch --prune 
--> delete remote ref branches that still shows after u delete them



git rebase -i head~(number of commits before current that you want to delete)
--> will open an editor jsut put 'd' before any commit u want to delete
--> after that save and close editor 

git branch -vv 
--> to view all current branches data

git reflog
--> view some important data on your head and branches changes 

git branch -b ur_local_branch_name
--> to make new local branch in your local repo (copying all from current branch as default)

git push -u  ur_local_branch_name
--> to make new remote branch for your new local branch

git push -f to final update the commit histroy at remote  
-- > all commits u done 'd' before them gone for ever !


git merge branch_to_merge -m "Merge msg"
--> to merge a branch with another branch (will not delete any of the two brancheds)

--> to copy already made local repo to already made remote repo please use either gh commands or github desktop
--> PLEASE DONT MAKE LOCAL AND REMOTE BRANCHES WITH DIFF NAMES PLEASE!! 
.....THIS IS NOT GIT DEFAULT AND CAUSESE MAMY HEADEACHES LATER ON IF U MANAGED TO DO IT IN FIRST PLACE

all important commands r here :
https://dev.classmethod.jp/articles/git-bash-commands/
https://www.youtube.com/watch?v=2sjqTHE0zok
https://www.youtube.com/playlist?list=PL6gx4Cwl9DGAKWClAD_iKpNC0bGHxGhcx
https://www.atlassian.com/git/tutorials/using-branches/git-checkout#:~:text=New%20Branches&text=The%20git%20branch%20command%20can,to%20switch%20to%20that%20branch.
https://www.w3docs.com/snippets/git.html


get letter meaning :

M: The file has been modified.
A: The file has been added to the index.
D: The file has been deleted from the working tree.
R: The file has been renamed.
C: The file has been copied.
U: The file is unmerged, meaning it has conflicts that need to be resolved.
!: file has merge conflict that need to be manually done ( both modified in local and remote)


# ############### (CMD & power shell) ############# IMPORTANT only

help <ur command> 
or <ur command> /? 
or <ur command>  --help
--> to read documentaion for the command u want (last one for cmder and linux only)

to use help in cmd 

*note:  using '/' or '\' is interchangable in cmd -most if time- also 'tab' will autocomplete ur command

code
--> opens vs code

start filename.exe 
--> (open any exe in directory)

start/min filename.exe 
--> (start any exe minimized)

command |clip   OR    clip <filename.txt
---> copy terminal  or any .txt to clip board

type nul > filename.txt
---> to make new .txt file
---> to write to file use (@echo ur text >> filename.txt) '>>' to append in new line not to overwrite
---> also check cat command and cp or copy on alzero crash course (link is down).


'cd .\folder1\folder2'                 
 --> change directory to a one inside ur current directory (dont miss dot in begining)

'cd C:\folder1\folder2'              
 --> change directory to a totally different one (u need to type full path starting from partition letter )

'cd ..'                              
  --> go back in directory only one location ( too location would be 'cd ..\..')

CHDIR /d  drive: path
--> (to change to another partion or drive)

'mkdir .\foldername'                   
--> make new folder inside current directory

'Remove-Item 'D:\temp\Test Folder1' 
--> removes the folder but it must be empty (to force remove append -recurse)

'New-Item filename.txt -ItemType file'                            
--> make a new file (u can make it .cpp and it will open in txt normally)

'New-Item filename.txt -path [UR FULL PATH HERE] -ItemType file'  
--> make a new file in another dir (u can make it .cpp and it will open in txt normally)

1..5 | foreach { new-item "FILENAME$_.txt" }
--> ***POWER SHELL ONLY!*** --> make multiple new files -5 in this example -  (1st file = FILENAME1 2nd  file= FILENAME2 ...)(make sure to apend by '$_' and if any thing comes after it put space between them)

1..5 | foreach { new-item -path [UR FULL PATH] }
-->multiple files in another dir (u can make an file typ like .cpp) ***POWER SHELL ONLY!***

'get-childitem'                         
--> will list all content -files and folders- inside current directory 

'g++ filname.cpp -o filename.exe' ; .\filename.exe'
--> ***POWER SHELL ONLY!*** (compile and run filname.exe in one statement)(filename.exe could be written only filename)
--> to do same in cmd in one command use '&&' instead of ';' (.\filename --> here'\' is NOT interchangable with '/')

'g++ -c filname.cpp -o filename.exe' ; .\filename.exe'
---> '-c' to just only compile filname not link it (output file is filename.o)

====> for more cpp commands in cmd : https://www.makeuseof.com/tag/15-cmd-commands-every-windows-user-know/

for /l %x in (1, 1, 100) do (
echo %x

echo any thing

)
--> for loop that works in cmer for more type for /?
--> if used in batch file use double percent '%%' before var name

'notepad'
--> open standard notepad

'cls'
--> clears all cmd screen

'Measure-Command {start-process 'FILE U WANT TO EXECUTE no qoutes!' -Wait}'
----> to calc execution time taken in this .exe file runtime.

====> on echo new line either using echo. or envisible 255 arg using alt+255 
 https://stackoverflow.com/questions/132799/how-can-i-echo-a-newline-in-a-batch-file#:~:text=You%20can%20insert%20an%20invisible,top%20of%20the%20querty%20keyboard!
 
====> for more usefull  general 'power shell' and 'cmd' commands : https://www.makeuseof.com/tag/15-cmd-commands-every-windows-user-know/

====> crash CLI course : https://youtube.com/playlist?list=PLDoPjvoNmBAxzNO8ixW83Sf8FnLy_MkUT


# ###############CODELITE#############IMPORTANT only
'ctrl+up\down' to swap lines places
'end' to go to the end of the line
'home' to go to the begining of line
'ctrl+tap' to switch between taps
'ctrl+y' redo last undo
'ctrl+tap+left or right' to delete word at once
'ctrl+scroll' zoom in or ou
'ctrl+shift+p' open  kebindings in Atom Editor
'ctrl+,' open settings in Atom editor
'Alt+F3' select only next same word  (ATOM shortcut)
'Alt+d' select all same next word (ATOM)
'ctrl+f' find and replace (ATOM)
select same word  or edit same word (not in codelite)  T_T

=====> all ECLIPSE  shortcut ctrl+ shft+L (see keybindings)
very usefull explanation for c functions at : https://www.ibm.com/support/knowledgecenter/ssw_ibm_i_74/rtref/scanf.htm

# ###############ATOM#############IMPORTANT only

'ctrl+shift+p' open  kebindings in Atom Editor
'ctrl+,' open settings in Atom editor
'Alt+F3' select only next same word  (ATOM shortcut)
'Alt+d' select all same next word (ATOM)
'ctrl+f' find and replace (ATOM)

======> more ATOM  shortcuts https://github.com/nwinkler/atom-keyboard-shortcuts

# ###############ECLIPSE#############IMPORTANT only


macro for build and run in eclipse (f12)

ctrl+d = delete all line

ctrl+shift+delete = delete to line end

ctrl +alt + up or down = duplicate line

alt + up or down= move line

alt+/ = auto complete

ctrl+space = auto complete +

alt+ shift +z = auto wrap code 

ctrl+f = find and replace/replace all

ctrl+k= find next 

ctrl+shift+k+ find previous

ctrl+shift+f= auto reformate code

ctrl+b =build code 

ctrl+y=redo

ctrl+# = commit

ctr+shift+l= shortcut menu




# ###############Jupyter in vs code #############IMPORTANT only
  
  ```c++
  
    YOUR BLOCK OF CODE 
    
  ```
  ---> to write any block of code  in (jupyter markdown - md - discord ... etc )of any language just replace C++ with your language


# ############### bash ubuntu#############IMPORTANT only
pwd 
-> (echo current dir)

export var=any-val 
-> (makes env var also could use set)

printenv 
-> ( prints all env variables 'set shows also but show many non needed not good like in cmder')

unset env_variable 
-> (to remove env. variable  'set env_var=' does not delete it like in cmder it jsut makes is empty)

htop 
-> (call it task maneger of  ubuntu & unix <3 btw made by someone called hisham) 

iotop 
-> (similar to htop but stats  more about disk usage by processes) 

sudo apt-get -y install app-name 
-> ( installs app and says yes to all prompts )

sudo shutdown -r now 
-> (reboots the system)

chmod u+x filename.sh 
-> (chmod modifies permissions of a file and this one give right to exec'x' and ower permission 'u')

kill task-id 
-> (kills task by id) 

pkill task-name 
-> ( kills task by name )

ps 
-> (print running processes that are attached to terminal only)

ps -e 
-> (print all running processes even ones not attached to terminal 'runs in background')

ll 
-> ( is modified ls command to show more details on files and dirs in current dir )

tmux ls 
-> to see all tmux session and which one your attached to

tmux new -d -s tmux_session_nam  'command-to-run-at-start'

-> ( name is optional also command to run is optional but must be inside single qotation)
-> (-d to start detached session with out it you detach to the new made tmux session)
-> (most power full command to isolate and silence a process and keep it working even if shell is closed some it may be risky cant exit cmder proberly)

tmux kill-session -t  session-num
-> (to kill a session of tmux)

& at end of commands
-> makes commands run in background ex : ./start_silent.sh &

nohup comnd.sh  and  comnd.sh & disown
-> also makes command run in background but kinda more detached ( search more on it )



# ############### tmux in bash ubuntu#############IMPORTANT only

ctrl + b c 
-> ( new tab )(press them seperatly ) 

ctrl + b <tab num> 
-> (moves to tab)

ctrl + b % 
->(split  new pan to right)

ctrl + b hold → 
-> (resize the pane also left resize)

ctrl + b → 
-> ( move to the right pan  also left moves to the right pan)

ctrl + b " 
-> (split down)(doesnt work for some reason)

ctrl + b   
-> ( searches tab by name and goes to it)

exit 
-> (gets out of program if in bash exits tmux)