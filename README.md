# My-Configs-Cmder
This repo contains my mini-tools and batch scripts that I use along with cmder aliases and configs

## Linux configuration backup

The [CachyOS + Hyprland/ML4W snapshot](./conf_backups/cachyos_hyprland_ml4w/README.md)
includes backup/restore scripts, local launchers, and regression tests. See its
README for restore prerequisites and intentionally excluded private data.


> ### if moved cmder to another path (in my case)  re-configure and check the following:

 * *edit all paths in* [`user_aliases.cmd`](./cmder/config/user_aliases.cmd)
 * *edit all environmental variables* : `cmder_root` , `conEmuDir` , `bin` , `path variables`  and any other variables*
 * edit paths in `Task Schdualer` tasks if you have tasks that depends on any tool in [`bin`](./cmder/bin)
 * cmder paths in `windows terminal preview cmder profile` and in `VS-code `
