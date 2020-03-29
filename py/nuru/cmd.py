from smanmi import network, util
from . import settings


logger = util.createLogger('sonar')


sock = network.create_udp_socket(
    settings.cmd_cmd_port, settings.address, timeout=1)
cmds = dict(setstate=dict(state=None, color=None), fc=0, midi=None)
while True:
    network.send(settings.integrator_sig_port, cmds)
    data = network.get_json(sock, None)
    if data:
        cmds['fc'] = data.get('fc', cmds['fc'])
        cmds['midi'] = data.get('midi', cmds['midi'])
        cmds['setstate'].update(data.get('setstate', {}))
        logger.info('-> %r', cmds)
