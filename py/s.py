"""Standalone signalin sender application."""

import socket, sys

commands = dict(
    frozenn='{"newstate": "frozen"}',
    test='{"newstate": "test"}',
    flash='{"newstate": "flash"}',
    std='{"newstate": "std"}',
    ooo='{"newstate": "ooo"}',
    std2='{"newstate": "std2"}',
    std3='{"newstate": "std3"}',
    sonaron='{"overrides": {"sonar": 0.0}}',
    sonaroff='{"overrides": {"sonar": 1.0}}',
    reset='{"overrides": ""}',
)

signalin_port = 6101

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for c in sys.argv[1:]:
    sent = False
    for command, msg in commands.items():
        if command.startswith(c):
            print('{} => {} : {}'.format(c, command, msg))
            sock.sendto(msg.encode('utf8'), ('localhost', signalin_port))
            sent = True
            break
    if not sent:
        print('*** DO NOT KNOW "{}"'.format(c))
