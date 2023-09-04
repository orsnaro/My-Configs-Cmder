@echo off
setlocal

rem clean ( close by force any open vbox process first )
taskkill /im "vbox*" /f

rem boot up the ubutnu virtual OS on VmBox 
rem (the serial is from ubunto setttingsin vbox or /bin/virt-ubuntu.lnk properties)
vboxheadless --startvm "ce742fbb-b557-4a7f-b1b1-1845ae9856e4" --password-id orsnaro --password C:\Users\OmarPc\virt-ubuntu-pass.txt 



rem continue only if vbox started ubunto os successfully
rem start ssh connection between "host win10 OS cmder and ubuntu virtual os"
rem (port and ip for both host and guest is configured in vmBox network nat settings)

rem run `sshvbox`

endlocal


