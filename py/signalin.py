"""Standalone signalin sender application."""

import socket, sys

commands = dict(
    test='{"state": "test"}',
    flash='{"state": "flash"}',
    std='{"state": "std"}',
)

signalin_port = 6101

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for c in sys.argv[1:]:
    sent = False
    for command, msg in commands.items():
        if command.startswith(c):
            print('{} => {} : {}'.format(c, command, msg))
            sock.sendto(msg, ('localhost', signalin_port))
            sent = True
            break
    if not sent:
        print('*** DO NOT KNOW "{}"'.format(c))
