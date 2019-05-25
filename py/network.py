import io, json, socket

import perf, settings, state, util


logger = util.NoLogger()


def create_udp_socket(port, timeout=0, address=settings.address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind((address, port))
    return sock


@perf.measure('get_json_and_address')
def get_json_and_address(sock, max_size=4096):
    try:
        data, address = sock.recvfrom(max_size)
    except io.BlockingIOError:
        return None, None
    try:
        data = json.loads(data.decode('utf8'))
        if 'state' in data:
            data['state'] = state.State(data['state'])
        return data, address
    except json.JSONDecodeError as e:
        logger.warning('Could not decode {!r} : {}'.format(data, e))
        return None, None


def get_json(sock, data, max_size=4096):
    newdata, _ = get_json_and_address(sock, max_size=max_size)
    if newdata:
        return newdata
    return data
