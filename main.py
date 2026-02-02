#!/usr/bin/env python3

import setproctitle
setproctitle.setproctitle("minecraft-monitor")

import socket
import subprocess
import time
import signal
import sys
from collections import deque
from mcstatus import JavaServer
from datetime import datetime

HOST = "0.0.0.0"
PORT = 25565
THRESHOLD = 12
WINDOW = 1
IDLE_TIMEOUT = 300  # 30 seconds for testing
SERVER_SCRIPT = "/home/alii/scripts/start_server.sh"
BACKUP_SCRIPT = "/home/alii/scripts/backup-server.sh"

attempts = deque()
server_process = None
server_running = False
last_player_time = None

def timestamp():
    """Return current timestamp string"""
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def run_backup():
    """Run the backup script"""
    print(f"{timestamp()} Running backup...")
    subprocess.run([BACKUP_SCRIPT])
    print(f"{timestamp()} Backup complete.")

def stop_server():
    """Stop the server gracefully"""
    global server_process, server_running
    
    if server_process and server_running:
        print(f"{timestamp()} Stopping Minecraft server...")
        
        # Send 'stop' command to the Minecraft server console
        try:
            server_process.stdin.write(b'stop\n')
            server_process.stdin.flush()
        except:
            # If that doesn't work, terminate the process
            server_process.terminate()
        
        # Wait for the server to shut down (give it up to 30 seconds)
        try:
            server_process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print(f"{timestamp()} Server didn't stop gracefully, forcing shutdown...")
            server_process.kill()
            server_process.wait()
        
        server_running = False
        run_backup()

def cleanup(signum, frame):
    """Run when Ctrl+C is pressed"""
    time.sleep(1)
    print(f"\n{timestamp()} Shutting down...")
    stop_server()
    print(f"{timestamp()} Shutdown complete.")
    sys.exit(0)

def get_player_count():
    """
    Check how many players are online
    Returns player count or None if can't connect
    """
    try:
        server = JavaServer.lookup(f"localhost:{PORT}")
        status = server.status()
        return status.players.online
    except Exception as e:
        # Server might still be starting up
        return None

def should_stop_server():
    """
    Check if server should be stopped
    Stops if no players for IDLE_TIMEOUT seconds
    """
    global last_player_time
    
    player_count = get_player_count()
    
    # If we can't check, don't stop (server might still be starting)
    if player_count is None:
        return False
    
    current_time = time.time()
    
    if player_count > 0:
        # Players online, update timestamp
        last_player_time = current_time
        return False
    else:
        # No players online
        if last_player_time is None:
            # First time seeing 0 players, start the timer
            last_player_time = current_time
            print(f"{timestamp()} No players online. Will shutdown in {IDLE_TIMEOUT/60} minutes if no one joins.")
            return False
        else:
            # Check how long it's been empty
            idle_time = current_time - last_player_time
            print(f"{timestamp()} No players for {idle_time:.1f} seconds.")
            if idle_time >= IDLE_TIMEOUT:
                print(f"{timestamp()} No players for {IDLE_TIMEOUT/60} minutes. Shutting down server.")
                return True
            return False

# Trap Ctrl+C
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def listen_once():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(1)
    conn, addr = sock.accept()
    print(f"{timestamp()} Connection attempt from {addr}")
    conn.close()
    sock.close()
    return time.time()

while True:
    try:
        # Only listen if server is NOT running
        if not server_running:
            ts = listen_once()
            attempts.append(ts)
            
            # Remove old timestamps outside the window
            while attempts and ts - attempts[0] > WINDOW:
                attempts.popleft()
            
            # Check if threshold reached
            if len(attempts) >= THRESHOLD:
                print(f"{timestamp()} {len(attempts)} attempts detected! Starting server...")
                server_running = True
                last_player_time = None
                
                # Start server with stdin pipe so we can send commands
                server_process = subprocess.Popen(
                    [SERVER_SCRIPT],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
                
                attempts.clear()
                
                # Give server time to start up
                print(f"{timestamp()} Waiting for server to start...")
                time.sleep(60)
        
        # If server is running, monitor it
        if server_running:
            # Check if server process has ended
            if server_process.poll() is not None:
                print(f"{timestamp()} Server process ended.")
                server_running = False
                run_backup()
                server_process = None
                print(f"{timestamp()} Listening for connections again...")
                continue
            
            # Check custom stop condition
            if should_stop_server():
                stop_server()
                server_process = None
                print(f"{timestamp()} Listening for connections again...")
                continue
            
            time.sleep(30)  # Check every 3 seconds
            
    except KeyboardInterrupt:
        cleanup(None, None)
    except Exception as e:
        print(f"{timestamp()} Error: {e}")
        time.sleep(0.1)