
import argparse, json, socket, sys

parser = argparse.ArgumentParser(description='Sends commands to lighter.')

parser.add_argument('--lighter_port', type=int, default=5618,
        help='Which port "lighter" is listening on.')
parser.add_argument('--address', type=str, default='localhost',
        help='Which address "lighter" is listening on.')

args = parser.parse_args()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
lighter_address = (args.address, args.lighter_port)

def send(lighter_message):
    lighter_message = json.dumps(lighter_message).encode('utf8')
    sock.sendto(lighter_message, lighter_address)

while True:
    sys.stdout.write('>>> ')
    sys.stdout.flush()
    words = sys.stdin.readline().strip().split(' ')

    if words == ['quit']:
        break
    elif len(words) == 1 and words[0] in ('start', 'search', 'wait'):
        send({'state': words[0]})
    elif len(words) == 2 and words[0] == 'id':
        send({'state': 'id', 'id': words[1]})
    elif words == ['help']:
        print('')
        print('start')
        print('search')
        print('wait')
        print('id NUM')
        print('quit')
        print('')
    else:
        print('*** unknown command - try "help"')

