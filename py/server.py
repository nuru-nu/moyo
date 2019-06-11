"""Standalone remote server application.

Depends on "pip install Flask".

Start like this: "FLASK_APP=server.py FLASK_DEBUG=0 flask run --host=0.0.0.0"

"""

import datetime, json, logging, socket, sys, time, threading

status_port = 6107
update_secs = 10

signalin_port = 6101

status_by_name_and_ip = {}

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


def get_json_and_address(sock, max_size=4096):
    try:
        data, address = sock.recvfrom(max_size)
    except socket.timeout:
        return None, None
    try:
        data = json.loads(data.decode('utf8'))
        return data, address[0]
    except json.JSONDecodeError as e:
        print('*** Could not decode {!r} : {}'.format(data, e))
        return None, None


def fmtt(t):
    if t > 3600 * 24:
        t = int(t / 3600)
        return '{}d{}h'.format(t // 24, t % 24)
    if t > 3600:
        t = int(t / 60)
        return '{}h{}m'.format(t // 60, t % 60)
    t = int(t)
    return '{}m{}s'.format(t // 60, t % 60)


def status_text(status_by_name_and_ip, top_n=0):
    lines = []
    for (name, ip), status in status_by_name_and_ip.items():
        ago = time.time() - status['t']
        lines += [(ago, '{}: {}={} [{} ago]'.format(
            ip, name, status['status'], fmtt(ago)))]
    return '\n'.join([line[1] for line in sorted(lines)])


def udp_loop():
    t0 = 0
    sock = create_udp_socket(status_port, timeout=1)
    while True:
        data, address = get_json_and_address(sock)
        if data:
            name = data['name']
            status = data['status']
            t = data['t']
            ip = data['ip']
            status_by_name_and_ip[(name, ip)] = dict(status=status, t=t)
        if time.time() - t0 < update_secs:
            continue
        t0 = time.time()
        print('\n' + str(datetime.datetime.now()))
        print(status_text(status_by_name_and_ip))


thread = threading.Thread(target=udp_loop)
thread.start()

signalin_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

commands = dict(
    test={"newstate": "test"},
    flash={"newstate": "flash"},
    std={"newstate": "std"},
    std2={"newstate": "std"},
    std3={"newstate": "std"},
    freeze={"newstate": "frozen"},
)


def send_signalin(signalin):
    msg = json.dumps(signalin).encode('utf8')
    logging.info('sending signalin={}'.format(msg))
    signalin_sock.sendto(msg, ('localhost', signalin_port))


from flask import Flask, request, Response  # NOQA
app = Flask(__name__)


@app.route("/")
def main_page():
    return """

<style type="text/css">
</style>

<h1>nuru shimoni</h1>

<pre>{status_by_name}</pre>

<div id="status"></div>

<div id="buttons"></div>

<script>
const commands = {commands}

let status = document.getElementById('status')

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
            status.innerText = (
                'status=' + req.status + '; responseText=' + req.responseText
            )
        }
    }
    req.open('GET', '/command?command=' + command, true)
    req.send()
}
</script>

""".replace(
        '{status_by_name}', status_text(status_by_name_and_ip)
    ).replace(
        '{commands}', json.dumps(list(commands.keys()))
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
