@echo off
setlocal

rem clean ( close by force any open vbox process first )
taskkill /im "vbox*" /f

rem boot up the ubutnu virtual OS on VmBox 
rem (the serial is from ubunto setttingsin vbox or /bin/virt-ubuntu.lnk properties)
vboxheadless --startvm "598c3280-7025-4efe-b9f8-58712460cfe2" --password-id orsnaro-vm --password C:\Users\OmarPc\virt-ubuntu-pass.txt 



rem continue only if vbox started ubunto os successfully
rem start ssh connection between "host win10 OS cmder and ubuntu virtual os"
rem (port and ip for both host and guest is configured in vmBox network nat settings)

rem run `sshvbox`

endlocal


