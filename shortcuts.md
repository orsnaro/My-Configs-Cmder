
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
/<searh query> + Enter (search in nvim use n,N to cycle between matches)
general:
  # Whether to automatically focus windows underneath the cursor.
  focus_follows_cursor: false 

  # Whether to jump the cursor between windows focused by the WM.
  cursor_follows_focus: true 

  # Whether to switch back and forth between the previously focused workspace
  # when focusing the current workspace.
  toggle_workspace_on_refocus: true

  # Whether to show floating windows as always on top.
  show_floating_on_top: true 

  # Amount to move floating windows by (eg. when using `alt+<ijkl>` on a floating window)
  floating_window_move_amount: "15%"

  # Whether to center new floating windows.
  center_new_floating_windows: true

  # *Strongly* recommended to set to 'false'. Whether to globally enable/disable
  # window transition animations (on minimize, close, etc). Set to 'unchanged'
  # to make no setting changes.
  window_animations: "false"

gaps:
  # Gap between adjacent windows.
  inner_gap: "10px"

  # Gap between windows and the screen edge.
  outer_gap: "4px"

# Highlight active/inactive windows with a colored border.
# ** Exclusive to Windows 11 due to API limitations.
focus_borders:
  active:
    enabled: true 
    color: "#16ffa1"

  inactive:
    enabled: true 
    color: "#ff0000"

bar:
  enabled: true
  always_on_top: true
  height: "18px"
  position: "bottom"
  opacity: 0.9
  background: *crust
  foreground: *mauve
  font_family: "Agave Nerd Font"
  font_size: "10px"
  padding: "4px 6px"
  offset_x: "0"
  offset_y: "0"
  border_radius: "0"

  components_left:
    - type: "workspaces"
      focused_workspace_background: "#ffffff33"
      displayed_workspace_background: "#00000033"
      default_workspace_background: "transparent"
      padding: "0 4px"
    - type: "window title"
  components_center:
    - type: "clock"
      # Documentation on formatting date/time string:
      # https://learn.microsoft.com/en-us/dotnet/standard/base-types/custom-date-and-time-format-strings
      time_formatting: "hh:mm tt  ddd MMM d"
  components_right:
    - type: "weather"
      latitude: 31.1341 
      longitude: 30.6460
      label: "{temperature_celsius}°C"
      label_sun: "☀️ {temperature_celsius}°C"
      label_moon: "🌙 {temperature_celsius}°C"
      label_cloud_moon: "🌙☁️ {temperature_celsius}°C"
      label_cloud_sun: "⛅ {temperature_celsius}°C"
      label_cloud_moon_rain: "🌙🌧️ {temperature_celsius}°C"
      label_cloud_sun_rain: "🌦️ {temperature_celsius}°C"
      label_cloud_rain: "🌧️ {temperature_celsius}°C"
      label_snow_flake: "❄️ {temperature_celsius}°C"
      label_thunderstorm: "⚡ {temperature_celsius}°C"
      label_cloud: "☁️ {temperature_celsius}°C"
    - type: "system tray"
    - type: "tiling direction"
      label_horizontal: "⮂"
      label_vertical: "⮁"
      background: "#ffffff33"
      margin: "0 4px"
      padding: "0 8px"
    - type: "binding mode"
      background: "#ffffff33"
      margin: "0 4px 0 0"
      padding: "0 8px"
    - type: "volume"
      padding: "0 4px"
      label_low: "🔊{volume_level}%"
      label_medium: "🔊{volume_level}%"
      label_high: "🔊{volume_level}%"
      label_mute: "🔊{volume_level}%"
    - type: "network"
      label_no_internet: "NC"
      label_ethernet: "Eth"
      label_wifi_strength_0: "WiFi: 0%"
      label_wifi_strength_25: "WiFi: 25%"
      label_wifi_strength_50: "WiFi: 50%"
      label_wifi_strength_75: "WiFi: 75%"
      label_wifi_strength_100: "WiFi: 100%"

workspaces:
  - name: "1"
    display_name: "1:Work"
    keep_alive: true

  - name: "2"
    display_name: "2:Work-sub"
    keep_alive: true

  - name: "3"
    display_name: "3:Search"
    keep_alive: true

  - name: "4"
    display_name: "4:Chat"
    keep_alive: true

  - name: "5"
    display_name: "5:Mail"
    keep_alive: false 

  - name: "6"
  - name: "7"
  - name: "8"
  - name: "9"

# when match process name don't append .exe
window_rules:
# SET ignore rules # 
# i.e.(I don't ever wnna tile those)
  
    # Do not manage picture-in-picture windows for browsers. Note that the default is for
    # English; change `match_title` to the window's title if you use another language.
  - command: "ignore"
    match_title: "[Pp]icture.in.[Pp]icture"
    match_class_name: "Chrome_WidgetWin_1|MozillaDialogClass"

  - command: "ignore"
    match_process_name: "Riot Client"

      # - command: "ignore"
      #match_process_name: ""

  # Task Manager requires admin privileges to manage and should be ignored unless running
  # the WM as admin.
  - command: "ignore"
    match_process_name: "/Taskmgr|ScreenClippingHost/"
      
  - command: "ignore"
    match_process_name: "Vortex"
  
  - command: "ignore"
    match_class_name: "VirtualConsoleClass"
    match_title: "*Cmder"
    match_process_name: "ConEmu64"

  - command: "ignore"
    match_process_name: "ConEmuC64"

  - command: "ignore"
    match_process_name: "ONCE_HUMAN"

  - command: "ignore"
    match_process_name: "LoadingBayInstaller"

# SET FLOATING RULES #
  - command: "set floating"
    match_process_name: "devenv"

  - command: "set floating"
    match_title: "LoadingBayInstaller"

  - command: "set floating"
    match_process_name: "Flow.Launcher"

  - command: "set floating"
    match_title: "AutoHotkey 64-bit"
    match_process_name: "AutoHotkeyUX"

  - command: "set floating"
    match_title: "Unity Hub"

  - command: "set floating"
    match_process_name: "qbittorrent"

  - command: "set floating"
    match_process_name: "obs64"

  - command: "set floating"
    match_title: "Window Spy for AHKv2"
      
  - command: "set floating"
    match_process_name: "ApplicationFrameHost"

  - command: "set floating"
    match_process_name: "Windows Explorer"

  - command: "set floating"
    match_process_name: "explorer"
    match_class_name: "WorkerW"

  - command: "set floating"
    match_class_name: "CabinetWClass"

  - command: "set floating"
    match_process_name: "mmc"
    match_title: "Task Scheduler"

  - command: "set floating"
    match_title: "Avast Free Antivirus"
    match_process_name: "AvastUI"

  # Launches system dialogs as floating by default (eg. File Explorer save/open dialog).
  - command: "set floating"
    match_class_name: "#32770"


# SET TILING RULE #
  - command: "set tiling"
    match_process_name: "Discord"
#    match_title: "*- Discord"
      
  - command: "set tiling"
    match_title: "*Microsoft Visual Studio Preview*"

  - command: "set tiling"
    match_title: "*Microsoft Visual Studio*"

# OTHER RULES #
  # Some applications (eg. Steam) have borders that extend past the normal border size.
  - command: "resize borders 0px -7px -7px -7px"
    match_process_name: "steam"

binding_modes:
  - name: "resize"
    keybindings:
      # Resize focused window by a percentage or pixel amount.
      - command: "resize width -2%"
        bindings: ["L", "Right"]
      - command: "resize width +2%"
        bindings: ["J", "Left"]
      - command: "resize height +2%"
        bindings: ["K", "Down"]
      - command: "resize height -2%"
        bindings: ["I", "Up"]
      # Press enter/escape to return to default keybindings.
      - command: "binding mode none"
        bindings: ["Escape", "Enter"]

keybindings:
  # Shift focus in a given direction.
  - command: "focus left"
    bindings: ["Alt+J", "Alt+J"]
  - command: "focus right"
    bindings: ["Alt+L", "Alt+L"]
  - command: "focus up"
    bindings: ["Alt+I", "Alt+I"]
  - command: "focus down"
    bindings: ["Alt+K", "Alt+K"]

  # Move focused window in a given direction.
  - command: "move left"
    bindings: ["Alt+Shift+J", "Alt+Shift+Left"]
  - command: "move right"
    bindings: ["Alt+Shift+L", "Alt+Shift+Right"]
  - command: "move up"
    bindings: ["Alt+Shift+I", "Alt+Shift+Up"]
  - command: "move down"
    bindings: ["Alt+Shift+K", "Alt+Shift+Down"]

  # Resize focused window by a percentage or pixel amount.
  - command: "resize width -2%"
    binding: "Alt+U"
  - command: "resize width +2%"
    binding: "Alt+P"
  - command: "resize height +2%"
    binding: "Alt+O"
  - command: "resize height -2%"
    binding: "Alt+H"

  # As an alternative to the resize keybindings above, resize mode enables resizing via
  # HJKL or arrow keys. The binding mode is defined above with the name "resize".

  - command: "toggle floating"
    binding: "Alt+T"

  - command: "binding mode resize"
    binding: "Alt+R"

  # Change tiling direction. This determines where new tiling windows will be inserted.
  - command: "tiling direction toggle"
    binding: "Alt+V"

  # Change focus between floating / tiling windows.
  - command: "focus mode toggle"
    binding: "Alt+Ctrl+Space"

  # Change the focused window to be floating / tiling.
  - command: "toggle floating"
    binding: "Alt+Shift+Space"

  # Change the focused window to be maximized / unmaximized.
  - command: "toggle maximized"
    binding: "Alt+X"

  # Minimize focused window.
  - command: "set minimized"
    binding: "Alt+M"

  # Close focused window.
  - command: "close"
    binding: "Alt+Shift+Q"

  # Kill GlazeWM process safely.
  - command: "exit wm"
    binding: "Alt+Shift+E"

  # Re-evaluate configuration file.
  - command: "reload config"
    binding: "Alt+Shift+R"

  # Launch CMD terminal (alternatively `exec wt` or `exec %ProgramFiles%/Git/git-bash.exe`
  # to start Windows Terminal and Git Bash respectively.
  - command: "exec cmder"
    binding: "Alt+Shift+Enter"

  # Focus the workspace that last had focus.
  - command: "focus workspace recent"
    binding: "Alt+Y"

  # Focus the next/previous workspace defined in `workspaces` config.
  - command: "focus workspace next"
    binding: "Alt+T"
  - command: "focus workspace prev"
    binding: "Alt+Shift+T"

  # Change focus to a workspace defined in `workspaces` config.
  - command: "focus workspace 1"
    binding: "Alt+1"
  - command: "focus workspace 2"
    binding: "Alt+2"
  - command: "focus workspace 3"
    binding: "Alt+3"
  - command: "focus workspace 4"
    binding: "Alt+4"
  - command: "focus workspace 5"
    binding: "Alt+5"
  - command: "focus workspace 6"
    binding: "Alt+6"
  - command: "focus workspace 7"
    binding: "Alt+7"
  - command: "focus workspace 8"
    binding: "Alt+8"
  - command: "focus workspace 9"
    binding: "Alt+9"

  # Move focused workspace to a monitor in a given direction.
  - command: "move workspace left"
    binding: "Alt+A"
  - command: "move workspace right"
    binding: "Alt+D"
  - command: "move workspace up"
    binding: "Alt+W"
  - command: "move workspace down"
    binding: "Alt+S"

  # Move focused window to a workspace defined in `workspaces` config.
  - commands: ["move to workspace 1", "focus workspace 1"]
    binding: "Alt+Shift+1"
  - commands: ["move to workspace 2", "focus workspace 2"]
    binding: "Alt+Shift+2"
  - commands: ["move to workspace 3", "focus workspace 3"]
    binding: "Alt+Shift+3"
  - commands: ["move to workspace 4", "focus workspace 4"]
    binding: "Alt+Shift+4"
  - commands: ["move to workspace 5", "focus workspace 5"]
    binding: "Alt+Shift+5"
  - commands: ["move to workspace 6", "focus workspace 6"]
    binding: "Alt+Shift+6"
  - commands: ["move to workspace 7", "focus workspace 7"]
    binding: "Alt+Shift+7"
  - commands: ["move to workspace 8", "focus workspace 8"]
    binding: "Alt+Shift+8"
  - commands: ["move to workspace 9", "focus workspace 9"]
    bindings: ["Alt+Shift+9"]


  

      # SOME COLOR SCHEMES # 
rosewater: &rosewater "#f5e0dc"
flamingo: &flamingo "#f2cdcd"
pink: &pink "#f5c2e7"
mauve: &mauve "#cba6f7"
red: &red "#f38ba8"
maroon: &maroon "#eba0ac"
peach: &peach "#fab387"
yellow: &yellow "#f9e2af"
green: &green "#a6e3a1"
teal: &teal "#94e2d5"
sky: &sky "#89dceb"
sapphire: &sapphire "#74c7ec"
blue: &blue "#89b4fa"
lavender: &lavender "#b4befe"
text: &text "#cdd6f4"
subtext1: &subtext1 "#bac2de"
subtext0: &subtext0 "#a6adc8"
overlay2: &overlay2 "#9399b2"
overlay1: &overlay1 "#7f849c"
overlay0: &overlay0 "#6c7086"
surface2: &surface2 "#585b70"
surface1: &surface1 "#45475a"
surface0: &surface0 "#313244"
base: &base "#1e1e2e"
mantle: &mantle "#181825"
crust: &crust "#11111b"
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
ctr+ shift+ p (all shortcuts vs code)
(NOT DEFAULT) `+4  ( collapse all folders in explorer )
(NOT DEFAULT) shift + ctrl + alt + f (fetch or one mouse button using xmouse)
(NOT DEFAULT)shift + ctrl + alt + c (commit all to local or one mouse button using xmouse)
(NOT DEFAULT)shift + p (push all to remote)
(NOT DEFAULT)shift + p (push all to remote)
(NOT DEFAULT) ~ + Q (toggle side activity bar))
(NOT DEFAULT)ctrl + j/k/l/i (move cursor a word 'instead of arrows')
(NOT DEFAULT)ctrl + alt + j/l (select word lift or right)


ctrl + k + release + o (separate vs code in totally diff windows)
ctrl+ tab   (switch between "active" tabs)
alt + left/right (navigate between active tabs)
ctrl+b (close side bar )
win+`  (close terminal side)
ctrl + g (go to line X)
ctrl + 0 ( go outside bracket)
alt + enter (open search result in formated tab)


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

`tmux kill-session -t  session-num or name`
-> (to kill a session of tmux)

`&` at end of commands
-> makes commands run in background ex : ./start_silent.sh &

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
