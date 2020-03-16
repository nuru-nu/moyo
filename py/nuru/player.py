import signal, socket, sys, threading, time

import numpy as np

from smanmi import audio, hotplug, network, perf, util
from . import settings

assert sys.argv[1] in ('out1', 'out2')

logger = util.createLogger('player')
effects = hotplug.HotPlug('.hotplug.effects', logger)
signals = {}

stats = dict(cb1=0, cb2=0)

buffer_factor = 10
out_names = (
    settings.out1_names if sys.argv[1] == 'out1'
    else settings.out2_names
)
out_rate = settings.out1_rate if sys.argv[1] == 'out1' else settings.out2_rate
port = (
    settings.player_sig_port if sys.argv[1] == 'out1'
    else settings.player2_sig_port)
effector = 'effector1' if sys.argv[1] == 'out1' else 'effector2'
audio.init(settings)
ai1 = audio.make_ai(out_names,  # stream_callback=stream_callback1,
                    rate=settings.out1_rate,
                    frames_per_buffer=int(
                        buffer_factor * settings.hop_secs * out_rate),
                    )
assert ai1 is not None, 'Could not find any of: {}'.format(settings.out1_names)
# ai1.output_stream.start_stream()
ai2 = None
ai2 = audio.make_ai(settings.out2_names,  # stream_callback=stream_callback2,
                    rate=settings.out2_rate,
                    frames_per_buffer=int(
                        buffer_factor * settings.hop_secs *
                        settings.out2_rate))
logger.info('ai2={}'.format(ai2))
running = True


def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False


@util.except_kill
def play_audio():
    global ai1, running
    zeros = np.zeros(int(settings.out2_rate * settings.hop_secs))
    while not signals and running:
        logger.info('waiting for signals...')
        time.sleep(1)
    while running:
        bufs = getattr(effects, effector)(zeros, signals)
        ai1.output_stream.write(audio.tostereo(bufs[0], bufs[1]).tostring())
    ai1.close()


@util.except_kill
def main_loop():
    global signals
    while running:
        try:
            signals = network.get_json(sock, signals)
        except socket.timeout:
            logger.warning('timeout get_json from integrator')


audio_thread = threading.Thread(target=play_audio)
audio_thread.start()

signal.signal(signal.SIGINT, signal_handler)
sock = network.create_udp_socket(port, settings.address, timeout=1)
main_loop()

logger.info('Stop playing.')
del ai1
if ai2:
    del ai2

print('\nPERF STATS:')
print(perf.stats())
