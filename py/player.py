import os, signal, sys, threading, time, traceback

import numpy as np

import audio, hotplug, network, perf, settings, util

import sys

assert sys.argv[1] in ('out1', 'out2')

logger = util.createLogger('player')
hp = hotplug.HotPlug(logger, modules=('effects',))
signals = {}

stats = dict(cb1=0, cb2=0)

# def stream_callback1(in_data, frame_count, time_info, status_flags):
#     stats['cb1'] = stats['cb1'] + 1
#     if 'state' in signals and signals['state'].state == 'frozen':
#         return (np.zeros(2 * frame_count, dtype=settings.dtype_np),
#                 pyaudio.paContinue)
#     bufs = hp.effects.effector1(np.zeros(frame_count // 2), signals)
#     # print(bufs[0].shape, bufs[1].shape)
#     return (audio.tostereo(bufs[0], bufs[1]).tostring(), pyaudio.paContinue)


# def stream_callback2(in_data, frame_count, time_info, status_flags):
#     stats['cb2'] = stats['cb2'] + 1
#     if 'state' in signals and signals['state'].state == 'frozen':
#         return (np.zeros(2 * frame_count, dtype=settings.dtype_np),
#                 pyaudio.paContinue)
#     bufs = hp.effects.effector2(np.zeros(frame_count // 2), signals)
#     return (audio.tostereo(bufs[0], bufs[1]).tostring(), pyaudio.paContinue)


buffer_factor = 10
out_names = (
    settings.out1_names if sys.argv[1] == 'out1'
    else settings.out2_names
)
out_rate = settings.out1_rate if sys.argv[1] == 'out1' else settings.out2_rate
port = settings.player_port if sys.argv[1] == 'out1' else settings.player2_port
effector = 'effector1' if sys.argv[1] == 'out1' else 'effector2'
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


def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False


running = True
zeros = np.zeros(int(settings.out2_rate * settings.hop_secs))


def play_audio():
    global ai1, running
    try:
        while not signals:
            logger.info('waiting for signals...')
            time.sleep(1)
        while running:
            bufs = getattr(hp.effects, effector)(zeros, signals)
            ai1.output_stream.write(audio.tostereo(bufs[0], bufs[1]).tostring())
    except:
        print('#### EXITING ####')
        traceback.print_exception(*sys.exc_info())
        os._exit(-999)

audio_thread = threading.Thread(target=play_audio)
audio_thread.start()

signal.signal(signal.SIGINT, signal_handler)
zerohop = np.zeros(settings.hop_size)
sock = network.create_udp_socket(port, timeout=None)
t0 = time.time()
while running:
    signals = network.get_json(sock, signals)
    if time.time() - t0 > 1e10:
        print(signals.get('left_drone'), signals.get('right_drone'), stats)
        t0 = time.time()
    # bufs = hp.effects.effector1(zeros, signals)
    # ai1.output_stream.write(audio.tostereo(bufs[0], bufs[1]).tostring())
    # ai2.output_stream.write(audio.tostereo(bufs[0], bufs[1]).tostring())
# audio_thread.join()

logger.info('Stop playing.')
del ai1
if ai2:
    del ai2

print('\nPERF STATS:')
print(perf.stats())
