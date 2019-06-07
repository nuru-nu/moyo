"""Standalone remote server application."""

import datetime, json, socket, time

status_port = 6107
update_secs = 10

status_by_name = {}

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

t0 = 0
sock = create_udp_socket(status_port, timeout=1)
while True:
    data = get_json(sock)
    if data:
        name = data['name']
        status = data['status']
        t = data['t']
        status_by_name[name] = dict(status=status, t=t)
    if time.time() - t0 >= update_secs:
        t0 = time.time()
        print('\n' + str(datetime.datetime.now()))
        for name, status in status_by_name.items():

            print('{}={} [{}s ago]'.format(
                name, status['status'], int(time.time() - status['t'])))
