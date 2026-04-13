#!/bin/bash

# 1. Define paths
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
echo win user: $WIN_USER
# SOURCE: Where your Edge data lives on C:
SOURCE_DIR="/mnt/c/Users/$WIN_USER/AppData/Local/Microsoft/Edge/User Data/Default"

# DEST: Your new backup location on the D: drive
DEST_DIR="/mnt/d/EdgeBackups/profile"

LOG_FILE="/mnt/d/EdgeBackups/sync.log"

# 2. Create the backup directory on D: if it doesn't exist
mkdir -p "$DEST_DIR"


# 3. Kill the Windows Edge process 
# We do this so the database files aren't "in use" during the backup
echo "Closing Edge to release file locks..."
taskkill.exe /F /IM msedge.exe /T > /dev/null 2>&1
taskkill.exe /F /IM MicrosoftEdgeUpdate.exe /T > /dev/null 2>&1
sleep 3 

# 4. Size & File Existense Checks (using 50KB for history and 40KB for login as a threshold for 'empty')
# 'stat -c%s' gets the file size in bytes
HIST_PATH="${SOURCE_DIR}/History"
LOGIN_PATH="${SOURCE_DIR}/Login Data"
HIST_SIZE=$(stat -c%s "$HIST_PATH" 2>/dev/null || echo 0)
LOGIN_SIZE=$(stat -c%s "$LOGIN_PATH" 2>/dev/null || echo 0)

# 5. Safety Check & Sync
if [ -s "$LOGIN_PATH" ] && [ -s "$HIST_PATH" ] && [ "$HIST_SIZE" -gt 50000 ] && [ "$LOGIN_SIZE" -gt 40000 ]; then
    # We add -v here so you can see the files moving in the log
    sudo rsync -av --delete "$SOURCE_DIR" "$DEST_DIR"
    echo "$(date): Edge Backup to D: Drive SUCCESS." >> "$LOG_FILE"
else
    echo "$(date): WARNING - Edge History/Login missing. Backup ABORTED to protect D: drive data." >> "$LOG_FILE"
fi