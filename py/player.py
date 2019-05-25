import signal, time

import numpy as np

import audio, hotplug, network, perf, settings, util

logger = util.createLogger('player')
hp = hotplug.HotPlug(logger)

ai1 = audio.AudioInterface(output=2, device_index=hp.effects.output_device_1)
ai2 = None
if hp.effects.output_device_2 is None or hp.effects.output_device_2 >= 0:
    ai2 = audio.AudioInterface(
        output=2, device_index=hp.effects.output_device_2)


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

    if 'state' in signals and signals['state'].state == 'frozen':
        time.sleep(settings.hop_secs)
        continue

    bufs = hp.effects.effector(zerohop, signals)
    ai1.output_stream.write(audio.tostereo(*bufs[:2]).tostring())
    if ai2:
        ai2.output_stream.write(audio.tostereo(*bufs[2:4]).tostring())


logger.info('Stop playing.')
del ai1
if ai2:
    del ai2

print('\nPERF STATS:')
print(perf.stats())
