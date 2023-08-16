@echo off
:: check if active.exe exists then run it  after that delete it 
if exist "%cd%\active.exe" (echo active.exe is running ... & echo. && active.exe && del active.exe)else(break)