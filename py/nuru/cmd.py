from smanmi import network, util
from . import settings


logger = util.createLogger('cmd')


sock = network.create_udp_socket(
    settings.cmd_cmd_port, '127.0.0.1', timeout=1)
cmds = dict()
while True:
    network.send(settings.integrator_sig_port, cmds)
    data = network.get_json(sock, None)
    if data:
        logger.info('Received command %s - DOING NOTHING', data)
