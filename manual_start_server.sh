#!/bin/bash
SERVER_DIR="$HOME/minecraft_server"
BACKUP_SCRIPT="$HOME/scripts/backup-server.sh"

# Function to run when Ctrl+C is pressed
cleanup() {
    echo ""
    echo "Server stopping... Running backup..."
    
    # Run the backup script
    if [ -f "$BACKUP_SCRIPT" ]; then
        "$BACKUP_SCRIPT"
    else
        echo "Backup script not found at $BACKUP_SCRIPT!"
    fi
    
    echo "Backup complete. Exiting."
    exit 0
}

# Trap multiple signals
trap cleanup SIGINT SIGTERM SIGHUP EXIT

# Check if directory exists
if [ ! -d "$SERVER_DIR" ]; then
    echo "Server directory $SERVER_DIR does not exist!"
    exit 1
fi

# Change to server directory
cd "$SERVER_DIR" || {
    echo "Failed to change to server directory!"
    exit 1
}

# Check if jar file exists
if [ ! -f "fabric_server_1.21.11.jar" ]; then
    echo "Server jar file not found!"
    exit 1
fi

# Run the server
echo "Starting Minecraft server from $SERVER_DIR..."
java -Xmx5G -Xms1G -jar fabric_server_1.21.11.jar nogui