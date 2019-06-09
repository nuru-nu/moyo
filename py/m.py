"""Terminal monitor."""

import argparse, datetime, time

import numpy as np

import network, settings

parser = argparse.ArgumentParser(
    description='Shows some monitoring information in terminal')
parser.add_argument('--hz', type=int, default=1,
                    help='Monitor frequency (hz).')
parser.add_argument('signals', type=str, nargs='+',
                    help='List of signals to monitor')
args = parser.parse_args()


def fmt(x):
    if isinstance(x, float):
        x = '%.3f' % x
    return x


def get(signals, signal):
    if '/' in signal:
        a, b = signal.split('/')
        return signals.get(a, {}).get(b)
    return signals.get(signal)


sock = network.create_udp_socket(settings.monitor_port, timeout=None)
t0 = 0
dt_buf = np.zeros(int(10 / settings.hop_secs))
loop_i = 0
t = time.time()
overrides = {}
sonar = -2
while True:

    data = network.get_json(sock, {})
    overrides = data.get('overrides', overrides)

    dt_buf[loop_i % len(dt_buf)] = time.time() - t
    loop_i += 1
    t = time.time()

    if data.get('signalin'):
        signalin = data['signalin']
        if 'sonar' in signalin:
            sonar = signalin['sonar']
            del signalin['sonar']
        if signalin:
            print('--- siganlin={}'.format(signalin))

    if t - t0 > 1 / args.hz:
        fps = 1. / dt_buf[:min(loop_i, len(dt_buf))].mean()
        now = datetime.datetime.now().strftime('%H:%M:%S')
        print('fps=%5.1f sonar=%.2f' % (fps, sonar), now, ' '.join([
            '{}={}'.format(signal, fmt(get(data, signal)))
            for signal in args.signals
        ]))
        if data.get('overrides'):
            print('+++ overrides={}'.format(data.get('overrides')))
        t0 = time.time()
