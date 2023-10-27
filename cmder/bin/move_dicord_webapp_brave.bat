@echo off
REM this .bat file is to run discord in web app ( cuz normal discord app syas am  banned ?!) then move it to verticall monitor (rest of command is in cmder alias 'dis' 
REM I dont run discrod directly instead i call .ps1 script to run it to not link discord to current opened cmder 
REM this can be done to any app i want to open in specific window

opera https://discord.com/channels/797143628215877672/889535812167938088  && timeout /t 2 
C:\Users\OmarPc\repo_CPP_COMP_study\cmder\bin\mmt.exe /MoveWindow 1 Process "brave.exe"  /WindowLeft -5  /WindowTop 0  /WindowWidth 910  /WindowHeight 1600