"""Standalone signalin sender application."""

import socket, sys

commands = dict(
    freeze='{"newstate": "frozen"}',
    test='{"newstate": "test"}',
    flash='{"newstate": "flash"}',
    std='{"newstate": "std"}',
    std2='{"newstate": "std"}',
    std3='{"newstate": "std"}',
)

signalin_port = 6101
update_secs = 10

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
