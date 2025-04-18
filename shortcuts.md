
# ----------------- NOTEPAD++ -----------------IMPORTANT only
> (F10) to toggle notepad++ task bar
> (ctrl + shift + m ) to open md preview
# -----------------Komorebi Tiling manager-----------------IMPORTANT only
> CONFIG AT : "C:\Program Files\whkd\bin\whkd_komorebi.whkdrc" & ENV VAR IS "WHKD_CONFIG_HOME"
```
alt + T (float/unfloat selected  "free")
alt + P (pause/unpause komorebi)
alt + I,J,K,L(move focus: up,left,down,right) (same as vim but made it more natural to me)
alt + shift + H,J,K,L(move window: up,left,down,right) (same as vim but made it more natural to me)
alt + 1,2,3.... (switch between workspaces)
alt + shift + 1,2,3.... (move app between workspaces)

misc.
alt + '+' (resize also '-')
alt + shift + r  ((reset tile grid)
alt + X,Y (flip windows horz and vertic)
alt + ctrl + shift + up,down,left,right(stack)
alt + ],[ (cycle in stack)
alt + ; right(unstack)
```
# -----------------NVIM-----------------IMPORTANT only
> NVIM binds are case Sensitive!
```
;,o,a (enter insert mode from normal mode. ';' overrides default 'i' for insert mode)
u ( undo last changes 'like ctrl-z' )
Esc (enter command mode)
v (enter visual mode from command mode 'V' in captial for visual line mode)
:!<cmd command> (executes cmder/cmd command while inside nvim liie `:!ls`)
/<searh query> + Enter (search in nvim use n,N to cycle between matches).
:help (obvious "any `:` is when ur in viusla/command mode not insert mode!")
:<line no,col>g g (move to specific line in text while in command mode)
<line no>g (go to the line number in text while in command or visual mode)
gg (go to top of text)
G (go to bottom of text)
V + <line no, col>gg (select lines until given line)
y (copy line "or to end of your cursor" while in visual mode)
p (paste line "pastes before the end of your cursor" while in visual mode)

misc.
:%s/<search_phrase>/<replace_phrase>/g (search and replace 'g' to replace all occurances)
move to begin of word + '*' (searches for this word in whole text)
:<command1> | :<command2> (chain commands using pipe'|')
:source ~/.vimrc (reloads the .vimrc "can be used with some other files)
```
# -----------------VS code-----------------IMPORTANT only
```
ctrl + shift + p (global menu in vs code)
ctrl + j (open terminal panel)

(NOT DEFAULT) `+4  ( collapse all folders in explorer ).
(NOT DEFAULT)ctrl + j/k/l/i (move cursor a word 'instead of arrows')
(NOT DEFAULT)ctrl + alt + j/l (select word lift or right)
(NOT DEFAULT) win+F5  (to use vscode debugger <build>)
(NOT DEFAULT) win+F6   ( to use vscode debugger <run>)
(NOT DEFAULT) shift + ` + Q ( to toggle side bar "activity bar")
(NOT DEFAULT) shift + ` + R ( change editor mode " text or hex... etc")
(NOT DEFAULT) shift + ` + 1 (toggle minimap)
(NOT DEFAULT) shift + ` + E (show extesions)
(NOT DEFAULT) shift + ` + w (show explorer)
(NOT DEFAULT) ctrl + space  (delete line)
(NOT DEFAULT) ctrl + alt + s (split editor)

(WONT WORK if tab is of editor type) alt + left/right (navigate between active tabs)

ctrl+ tab   (switch between "active" tabs)
ctrl + shift + /(duplicate selected lines)
ctrl + k + release + o (separate vs code in totally diff windows)
ctrl + b (close side bar ).
ctrl + g (go to line X)
ctrl + 0 ( go outside bracket)
alt + enter (open search result in formated tab).
shift + d    (select highlited)
ctrl + /     (comment lines)
ctrl + I (suggestions)
(NOT DEFAULT) win+F6   ( to use vscode debugger <run>)

ctrl + alt + N (to build and run  using code runner in terminal <no debugging> )


--> for more  https://code.visualstudio.com/shortcuts/keyboard-shortcuts-windows.pdf

```

# -----------------VS Studio-----------------IMPORTANT only
(NOT DEFAULT)
```
ctrl + Q (global search in VS studio)
ctrl + alt + L (open explorer)
ctrl + W (close file)
ctrl + shift + / (dup line / selected)
ctrl + \ ( toggle block comment)
ctrl + D (select highlighted / select next occurance)
ctrl  + 1 , 1 (open terminal)
ctrl + space (view suggestion list)
ctrl + m , f (format all document)
ctrl + tab (switch between opened files)
ctrl + p (switch to file fast by typing name like vs code)(to specifically search files not classes or etc use `f:<file name>`) (default is ctrl + T or ctrl + ,)
Alt + T (toggle whitespaces render)
ctrl + shift + x ( line delete )
ctrl + x ( line cut )
alt + w then V (new window vertical)
alt + w then H (new window horz)
ctrl + M, ctrl + A (COLLAPSE ALL!)
ctrl + M, ctrl + X (EXPAND ALL!)
ctrl + M, ctrl + S (collapse region)
ctrl + M, ctrl + E (expand region)
shft + Alt + = (expand The Hilight highlight more)

```


#  -----------------(Cmder)-----------------IMPORTANT only
```
`cmd`
--> to run/nest new cmd inside cmder/cmd/powershell ( not cmder alias is windows default argument)

`ps`
-->(NOT DEFAULT)(cmder alias)  to run powershell inside the current cmd/cmder/powershell and nest them

`set`
--> to echo all windaws deafult arguments and variables

`code`
--> opens vs code

`code .`
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


`command | clip   OR clip < filename.txt`
--->   copy terminal o\p or any .txt to the clipboard

`CHDIR /d  drive: path`
--> (to change to another partion or drive)

`start filename.exe`
--> (open any exe in directory)

ctrl + r
--> reverse search command histroy ( if ur wanted command is before found one just PRESS ctr + r again until u found it )
ctrl + s
--> forward search in cmder

arrow right
--> get the found search to terminal


`winget list`
--> list all installed programs versions and if there is newer available version for upgrade

`winget upgrade --all`
--> update all programs installed

`dir  "\*part_of_filename*"  /s`
--> searches for ur file (for linux and cmder u can use 'find' also try find --help)
-->The backslash tells dir to search from the root directory of the current drive.
--> to search for a dir not a file use:

 `dir "\*part_of_dir_name*" /AD /S`
--> /A- Displays files with specified attributes. D-May the attribute be Directories

`xxd filename.extention`
--> to memory view the file in hexadecimal dump (for bash only + cmder)
`xxd filename.extention | vim`
--> same as previous put to open it inside vim


`starz github-username`
--> to install 'npm install -g starz' . it's an CMD tool that shows total gihub account stars

 `tasklist | grep *your running process name*`
 --> this will only search and echo the runing tasks that has same name if there is any
 --> (user defined alias for tasklist command is 'tsk' or 'task'

 `taskkill /im runing_task_name`
-->kill task using image name (omit /im to kill task by process number PID)

`python -m venv virtual_env_name`
--> make new python virtual env

`vritual_env_path/Scripts/activate`
--> start your virtual env

`deactivate`
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

*terminal
Ctrl + Alt + U : Traverse up in directory structure (lovely feature!)
End, Home, Ctrl : Traversing text with as usual on Windows
Ctrl + R : History search
Shift + Mouse : Select and copy text from buffer

win + alt + a : open ConEmu about window ( from there you can find monitors ids)
```

#  -----------------(Git) -----------------IMPORTANT only
```
https://kbroman.org/github_tutorial/pages/first_time.html
-->docs on: connect and auth git with github acc for push

`create-shortcut "source path" "destination path"`
--> create a shortcut (must apend destination path with "ShortcutName.lnk")

`git checkout   "hash or branch name"`
--> move head (ure current snapshot) to older snapshot of ur dir
--> or move head to another local branch

`git fetch --prune`
--> delete remote ref branches that still shows after u delete them



`git rebase -i head~(number of commits before current that you want to delete)`
--> will open an editor jsut put 'd' before any commit u want to delete
--> after that save and close editor

`git branch -vv`
--> to view all current branches data

`git reflog`
--> view some important data on your head and branches changes

`git branch -b ur_local_branch_name`
--> to make new local branch in your local repo (copying all from current branch as default)

`git push -u ur_local_branch_name`
--> to make new remote branch for your new local branch

`git push -f` to final update the commit histroy at remote
-- > all commits u done 'd' before them gone for ever! DONT USE `-f` unless needed


`git merge branch_to_merge -m "Merge msg"`
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

```
# -----------------(power shell & CMD)-----------------IMPORTANT only
```
`help <ur command>`
or `<ur command> /?`
or `<ur command>  --help`
--> to read documentaion for the command u want (last one for cmder and linux only)

to use help in cmd

*note:  using '/' or '\' is interchangable in cmd -most if time- also 'tab' will autocomplete ur command

`code`
--> opens vs code

`start filename.exe`
--> (open any exe in directory)

`start/min filename.exe`
--> (start any exe minimized)

`command |clip   OR    clip <filename.txt`
---> copy terminal  or any .txt to clip board

`type nul > filename.txt`
'dir "" > filename.txt'
---> to make new .txt file
---> to write to file use (@echo ur text >> filename.txt) '>>' to append in new line not to overwrite
---> also check cat command and cp or copy on alzero crash course (link is down).

`cd .\folder1\folder2`
 --> change directory to a one inside ur current directory (dont miss dot in begining)

`cd C:\folder1\folder2`
 --> change directory to a totally different one (u need to type full path starting from partition letter )

`cd ..`
--> go back in directory only one location ( too location would be 'cd ..\..')

`CHDIR /d  drive: path`
--> (to change to another partion or drive)

`mkdir .\foldername`
--> make new folder inside current directory

`Remove-Item 'D:\temp\Test Folder1`
--> removes the folder but it must be empty (to force remove append -recurse)

`New-Item filename.txt -ItemType file`
--> make a new file (u can make it .cpp and it will open in txt normally)

`New-Item filename.txt -path [UR FULL PATH HERE] -ItemType file`
--> make a new file in another dir (u can make it .cpp and it will open in txt normally)

`1..5 | foreach { new-item "FILENAME$_.txt" }`
--> ***POWER SHELL ONLY!*** --> make multiple new files -5 in this example -  (1st file = FILENAME1 2nd  file= FILENAME2 ...)(make sure to apend by '$_' and if any thing comes after it put space between them)

`1..5 | foreach { new-item -path [UR FULL PATH] }`
-->multiple files in another dir (u can make an file typ like .cpp) ***POWER SHELL ONLY!***

`get-childitem`
--> will list all content -files and folders- inside current directory

`g++ filname.cpp -o filename.exe' ; .\filename.exe`
--> ***POWER SHELL ONLY!*** (compile and run filname.exe in one statement)(filename.exe could be written only filename)
--> to do same in cmd in one command use '&&' instead of ';' (.\filename --> here'\' is NOT interchangable with '/')

`g++ -c filname.cpp -o filename.exe' ; .\filename.exe`
---> '-c' to just only compile filname not link it (output file is filename.o)

====> for more cpp commands in cmd : https://www.makeuseof.com/tag/15-cmd-commands-every-windows-user-know/

\```batch
for /l %x in (1, 1, 100) do (
echo %x

echo any thing

)
\```

--> for loop that works in cmder for more type for /?
--> if used in batch file use double percent '%%' before var name

'notepad'
--> open standard notepad

`cls`
--> clears all cmd screen

`Measure-Command {start-process 'FILE U WANT TO EXECUTE no qoutes!' -Wait}`
----> to calc execution time taken in this .exe file runtime.

====> on echo new line either using echo. or envisible 255 arg using alt+255
 https://stackoverflow.com/questions/132799/how-can-i-echo-a-newline-in-a-batch-file#:~:text=You%20can%20insert%20an%20invisible,top%20of%20the%20querty%20keyboard!

====> for more usefull  general 'power shell' and 'cmd' commands : https://www.makeuseof.com/tag/15-cmd-commands-every-windows-user-know/

====> crash CLI course : https://youtube.com/playlist?list=PLDoPjvoNmBAxzNO8ixW83Sf8FnLy_MkUT

```

# -----------------(bash in ubuntu)-----------------IMPORTANT only
```

`pwd`
-> (echo current dir also use env. var. `~`)

`export var=any-val`
-> (makes env. var. also could use set)

`printenv`
-> (prints all env. variables: set shows variables also but along with many non-needed scripts/info. Not good like 'set' in cmder)

`unset env_variable`
-> (to remove env. variable  'set env_var=' does not delete it like it does in cmder. It jsut makes variable empty)

`htop`
-> (call it task maneger of  ubuntu & unix <3 btw made by someone called hisham)

`iotop`
-> (similar to htop but stats: provides more deatails about disk usage by processes)

`sudo apt-get -y install app-name `
-> ( installs apps and auto  'yes' to all prompts )

`sudo shutdown -r now`
-> (reboots the system)

`chmod u+x filename.sh`
-> (chmod modifies permissions of a file: this one gives right to exec'x' and owmer permission 'u')

`kill task-id`
-> (kills task by pid)

`pkill task-name`
-> ( kills task by name )

`ps`
-> (print running processes that are attached to terminal only)

`ps -e`
-> (print all running processes even ones not attached to terminal 'runs in background')

`ll`
-> (modified 'ls' command to show more verbose details on files and dirs in current directory)

`tmux ls`
-> to see all tmux sessions and which one you're attached to

`tmux new -d -s tmux_session_nam  'command-to-run-at-start'`
-> (-s session-name is optional. Also command to start session with  is optional.  must be inside single qotation)
-> (-d to start detached session with out it you attach to the new made tmux session)
-> (most power full command to isolate and silence a process and keep it working even if shell is closed. somtimes  may be risky: cant exit cmder/win-terminal-preview proberly)

`tmux kill-session -t  <session-num or name>`
-> (to kill a session of tmux)

`tmux switch <session-num or name>`
-> (to switch to antother session and detach from the current)

`&` at end of commands
-> makes commands run in background ex : ./start_silent.sh &

`ctr+b` then `p` 
-> switch to last tmux window (windows are listed in status bar)

`ctrl+b` then `%`
-> split tmux pan to right

`ctrl+b` then arrows
-> move between tmux panes

`nohup comnd.sh`  and  `comnd.sh & disown`
-> also makes command run in background but kinda more detached ( search more on it )


`drwx-rwx-rwx` or `d-7
-> this permission says that its a dir and owner group and others all have read write execute permissons
x -> this permission has value '001' or in dec 1 and its an execution permission
w -> //   //         //   //   '010' or in dec 2 and its an write permission
r -> //   //         //   //   '100' or in dec 4 and its a  read permision
d -> not actual permission but tells us that this is a `dir` or if '-' instead of 'd' then its a `file`

u -> in `chmod` command means owner
g -> in `chmod` command means group
o -> in `chomd` command means others

`chmod ugo+rwx foo.sh`
-> this example comand give all fileOwner-group-others the permission to read write and execute
-> in numeric values we code write `chmod 777 foo.sh` this does same as prev. command
```


# -----------------(tmux in bash ubuntu)-----------------IMPORTANT only
```
ctrl + b c
-> (tabbing: new tab )(press them seperatly)

ctrl + b <tab num>
-> (switches to tab)

ctrl + b %
->(panning: split a new pan to right)

ctrl + b hold →
-> (resize the pane)

ctrl + b →
-> ( switch to the right pan  also : ctrl+b+left moves to the left pan)

ctrl + b "
-> (split down)

ctrl + b + '
-> (searches tab by name and switches to it)

 exit
-> (gets out of program. if in bash exits tmux)

more: 
https://hamvocke.com/blog/a-quick-and-easy-guide-to-tmux/
```

# -----------------Unity Editor-----------------IMPORTANT only
```
global search [Ctrl + K]
scroll between Scene Tools: [Q-W-E-R-T-Y]
Scene Vertex Snap: hold[V]
Scene Grid Snap: hold[Ctrl]
Toggle Play: [Space]
Next Frame: [.]
Previous Frame: [,]
Play: [Ctrl/Cmd + P]
Pause: [Ctrl /Cmd + Shift + P]
Step: [Ctrl/Cmd + Alt + P]
Create Empty Game Object: [Ctrl/Cmd + Shift + N]
Duplicate: [Ctrl/Cmd + D]
Invert Selection: [Ctrl/Cmd + I]
Deselect All: [Shift + D]
Move Object to View: [Ctrl/Cmd + Alt + F]
Maximize Game View: [Shift + Space]
Open Console: [Ctrl + Shift + C]
make camera same as scene view: [ctrl + shift + f]
shrink all child dirs: [alt + click on shrink arrow]
manual refresh assets [ctrl + r] (if u wnna enable auto refresh edit -> preferences -> Asset pipeline)
```
