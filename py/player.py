import signal, time

import numpy as np
import pyaudio

import audio, hotplug, network, perf, settings, util

logger = util.createLogger('player')
hp = hotplug.HotPlug(logger, modules=('effects',))


def stream_callback1(in_data, frame_count, time_info, status_flags):
    if 'state' in signals and signals['state'].state == 'frozen':
        return (np.zeros(2 * frame_count, dtype=settings.dtype_np),
                pyaudio.paContinue)
    bufs = hp.effects.effector1(np.zeros(frame_count), signals)
    return (audio.tostereo(*bufs[:2]).tostring(), pyaudio.paContinue)


def stream_callback2(in_data, frame_count, time_info, status_flags):
    if 'state' in signals and signals['state'].state == 'frozen':
        return (np.zeros(2 * frame_count, dtype=settings.dtype_np),
                pyaudio.paContinue)
    bufs = hp.effects.effector2(np.zeros(frame_count), signals)
    return (audio.tostereo(*bufs[:2]).tostring(), pyaudio.paContinue)


ai1 = audio.make_ai(settings.out1_names, stream_callback=stream_callback1)
assert ai1 is not None, 'Could not find any of: {}'.format(settings.out1_names)
ai2 = audio.make_ai(settings.out2_names, stream_callback=stream_callback2)
ai2 = None  # currently not supported
logger.info('ai2={}'.format(ai2))


def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False


signal.signal(signal.SIGINT, signal_handler)
zerohop = np.zeros(settings.hop_size)
sock = network.create_udp_socket(settings.player_port)
signals = {}
running = True
while running:
    signals = network.get_json(sock, signals)
    time.sleep(settings.hop_secs)


logger.info('Stop playing.')
del ai1
if ai2:
    del ai2

print('\nPERF STATS:')
print(perf.stats())
