@echo off
REM this .bat file is to run discord then move it to verticall monitor (rest of command is in cmder alias 'dis' 
REM I dont run discrod directly instead i call .ps1 script to run it to not link discord to current opened cmder 
REM this can be done to any app i want to open in specific window

powershell.exe -ExecutionPolicy Bypass -File C:\Users\OmarPc\repo_CPP_COMP_study\cmder/bin/openDiscord.ps1 && timeout /t 2 > nul

