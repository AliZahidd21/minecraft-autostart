#!/bin/bash
HOME="/home/alii"
SOURCE_FOLDER="/home/alii/minecraft_server"
TMP_NAME="backup.zip"
SAFE_NAME="backupsafe.zip"

# Local destinations
LOCAL_DESTS=("/MC" "$HOME/MC")

# Rclone destination
RCLONE_REMOTE="gdrive:/backup"

# Step 1: Check if source exists
if [ ! -d "$SOURCE_FOLDER" ]; then
    echo "Source folder $SOURCE_FOLDER does not exist!"
    exit 1
fi

# Step 2: Create zip backup
echo "Creating backup..."
zip -rq -1 "$TMP_NAME" "$SOURCE_FOLDER"
if [ $? -ne 0 ]; then
    echo "Failed to create zip!"
    exit 1
fi

# Step 3: Handle local destinations
echo "Copying to local destinations..."
for DEST in "${LOCAL_DESTS[@]}"; do
    mkdir -p "$DEST"
    cp "$TMP_NAME" "$DEST/$TMP_NAME"
    if [ $? -ne 0 ]; then
        echo "Failed to copy to $DEST!"
        continue
    fi
    if [ -f "$DEST/$SAFE_NAME" ]; then
        rm "$DEST/$SAFE_NAME"
    fi
    mv "$DEST/$TMP_NAME" "$DEST/$SAFE_NAME"
    echo "Backup for $DEST complete."
done

rclone cleanup gdrive:

# Step 4: Handle rclone destination
echo "Uploading to Google Drive..."

# Upload with temporary name first
rclone copy "$TMP_NAME" "$RCLONE_REMOTE" \
    --drive-chunk-size 128M \
    --transfers 1 \
    --checkers 8

if [ $? -eq 0 ]; then
    echo "Upload successful."
    
    # Delete old backup only AFTER successful upload
    if rclone lsf "$RCLONE_REMOTE/$SAFE_NAME" &>/dev/null; then
        echo "Deleting old backup from Google Drive..."
        rclone delete "$RCLONE_REMOTE/$SAFE_NAME"
    fi
    
    # Rename the uploaded file to safe name
    rclone moveto "$RCLONE_REMOTE/$TMP_NAME" "$RCLONE_REMOTE/$SAFE_NAME"
    
    echo "Backup to Google Drive complete."
else
    echo "Failed to upload to Google Drive!"
fi

rm "$TMP_NAME"