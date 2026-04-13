#!/bin/bash

# 1. Define paths
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')

# BACKUP_SOURCE: Your backup folder on the D: drive
RESTORE_SOURCE="/mnt/d/EdgeBackups/profile"

# BROWSER_DEST: The live Edge folder on your C: drive
RESTORE_DISTNATION="/mnt/c/Users/$WIN_USER/AppData/Local/Microsoft/Edge/User Data/Default"

LOG_FILE="/mnt/d/EdgeBackups/restore.log"

# 2. Check if D: drive is even mounted
if [ ! -d "$RESTORE_DISTNATION" ]; then
    echo "$(date): ERROR - D: drive backup folder not found. Is the drive plugged in?" >> "$LOG_FILE"
    exit 1
fi

# 3. Kill the Windows Edge process 
# We do this so the database files aren't "in use" during the restore
echo "Closing Edge to release file locks..."
taskkill.exe /F /IM msedge.exe /T > /dev/null 2>&1
taskkill.exe /F /IM MicrosoftEdgeUpdate.exe /T > /dev/null 2>&1
sleep 3 

# 4. Restore the data
# Using -a (archive) to preserve the structure and --delete to wipe any corrupted files in the destination
sudo rsync -av --delete "$RESTORE_SOURCE" "$RESTORE_DISTNATION"

echo "$(date): Edge Restore from D: drive COMPLETED." >> "$LOG_FILE"