"""Standalone remote server application.

Depends on "pip install Flask".

Start like this: "FLASK_APP=server.py FLASK_DEBUG=0 flask run --host=0.0.0.0"

"""

import datetime, json, logging, socket, sys, time, threading

status_port = 6107
update_secs = 10

signalin_port = 6101

status_by_name = {}

logger = logging.getLogger('server')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


def create_udp_socket(port, timeout=0, address='0.0.0.0'):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind((address, port))
    return sock

def get_json(sock, max_size=4096):
    try:
        data, address = sock.recvfrom(max_size)
    except socket.timeout:
        return None
    try:
        data = json.loads(data.decode('utf8'))
        return data
    except json.JSONDecodeError as e:
        print('*** Could not decode {!r} : {}'.format(data, e))
        return None

def udp_loop():
    t0 = 0
    sock = create_udp_socket(status_port, timeout=1)
    while True:
        data = get_json(sock)
        if data:
            name = data['name']
            status = data['status']
            t = data['t']
            status_by_name[name] = dict(status=status, t=t)
        if time.time() - t0 < update_secs:
            continue
        t0 = time.time()
        print('\n' + str(datetime.datetime.now()))
        for name, status in status_by_name.items():
            print('{}={} [{}s ago]'.format(
                name, status['status'], int(time.time() - status['t'])))

thread = threading.Thread(target=udp_loop)
thread.start()

signalin_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

commands = dict(
    test={"newstate": "test"},
    flash={"newstate": "flash"},
    std={"newstate": "std"},
    freeze={"newstate": "freeze"},
)

def send_signalin(signalin):
    msg = json.dumps(signalin).encode('utf8')
    logging.info('sending signalin={}'.format(msg))
    signalin_sock.sendto(msg, ('localhost', signalin_port))

from flask import Flask, request, Response
app = Flask(__name__)

@app.route("/")
def main_page():
    return """

<style type="text/css">
</style>

<h1>nuru shimoni</h1>

<pre>{status_by_name}</pre>

<div id="buttons"></div>

<script>
const commands = ['test', 'flash', 'std', 'freeze']

let buttons = document.getElementById('buttons')
commands.forEach(function(command) {
    let button = document.createElement('button')
    button.onclick = function() {
        send_command(command)
    }
    button.innerText = command
    buttons.appendChild(button)
})

function send_command(command) {
    console.log('sending command', command)
    req = new XMLHttpRequest()
    req.onreadystatechange = function() {
        if (req.readyState === XMLHttpRequest.DONE) {
            console.log(req.status, req.responseText)
        }
    }
    req.open('GET', '/command?command=' + command, true)
    req.send()
}
</script>

""".replace(
        '{status_by_name}', json.dumps(status_by_name, indent=2)
    )

@app.route("/command", methods=("GET", "POST"))
def send_command():
    command = request.args['command']
    try:
        send_signalin(commands.get(command))
        return Response(status=200)
    except socket.error as e:
        logging.error('socket.error={}'.format(e))
        return Response(str(e), status=500, mimetype='text/plain')
