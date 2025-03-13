"""Records audio & extracts FFT."""

import argparse
import logging
import os
import signal as pysig
import time

# Avoid BLAS/PACK using all cores for realtime matmul (wav2features).
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np  # noqa=E402 type: ignore

from nurulib import audio, hotplug, network, perf, util  # noqa=E402
from . import features, recording, settings  # noqa=E402

parser = argparse.ArgumentParser(
    description='Records audio & computes features for NURU.')
parser.add_argument('--debug', action='store_true', help='Show debug logs.')
args = parser.parse_args()

assert os.path.isdir(settings.recorder_dir), (
    'recorder_dir="%s" not found' % settings.recorder_dir)

logger = util.createLogger('recorder', debug=args.debug)
if settings.timetracing:
    tt = util.Timetracer('recorder', settings.timetraces_dir)
if settings.log_debug:
    logger.setLevel(logging.DEBUG)

hp_signals = hotplug.HotPlug('.hotplug.signals', logger)
hp_effects = hotplug.HotPlug('.hotplug.effects', logger)

running = True


def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False


pysig.signal(pysig.SIGINT, signal_handler)


class InputStreamer(object):

    def __init__(self, audio_interface):
        self.audio_interface = audio_interface

        # will be initialized when .freeze(false) is called the first time
        self.t = 0
        self.t0 = time.time()
        self.data = np.zeros(settings.buf_size, dtype=np.float32)
        self.frozen = False

    def freeze(self, frozen):
        if self.frozen == frozen:
            return
        if frozen:
            self.audio_interface.input_stream.stop_stream()
        else:
            self.audio_interface.input_stream.start_stream()
        self.frozen = frozen

    @perf.measure('InputStreamer.read')
    def read(self, samples):
        data = self.audio_interface.input_stream.read(
            samples, exception_on_overflow=False)
        data16 = np.frombuffer(data, settings.dtype_np)
        if settings.in_channels == 2:
            data16l, data16r = audio.fromstereo(data16)
            data16 = settings.in_channel_combination(data16l, data16r)
        data = util.int16_to_float(data16)
        data = hp_effects.microphone(data)
        self.t += float(len(data)) / settings.rate
        return data

    def clear_buffers(self):
        while self.audio_interface.input_stream.get_read_available():
            n = self.audio_interface.input_stream.read(
                self.audio_interface.input_stream.get_read_available())
            logger.info('Clearing buffers : read n={} bytes.'.format(n))

    def get(self):
        self.data = np.roll(self.data, shift=-settings.hop_size, axis=0)
        self.data[-settings.hop_size:] = self.read(settings.hop_size)
        return self.data

    def get_dt(self):
        return time.time() - self.t0 - self.t

    def reset_audio_interface(self, audio_interface):
        self.audio_interface = audio_interface
        self.player.reset_audio_interface(audio_interface)


i = 0
i_o = 0

logger.info('Using in_channels={}'.format(settings.in_channels))
audio.init(settings)
ai0 = audio.AudioInterface(input=settings.in_channels, output=1)
input_streamer = InputStreamer(ai0)
last_reset_t = time.time()

status_sender = network.StatusSender(name='recorder', logger=logger)


@perf.measure('get_signals')
def get_signals(features):
    return hp_signals.audio_runner(features=features, t=time.time())


sock = network.create_udp_socket(settings.recorder_cmd_port, '127.0.0.1')
record = playback = None
subsample = 1
lfeats = None
while running:

    if (settings.reset_secs
            and time.time() - last_reset_t > settings.reset_secs):
        logger.info('Re-initializing input_streamer.')
        del ai0
        ai0 = audio.AudioInterface(input=1)
        input_streamer.reset_audio_interface(ai0)
        last_reset_t = time.time()

    feats = None
    if playback:
        feats = playback.read(loop=True)
        ai0.play(feats.wav)
    if not feats:
        data = input_streamer.get()
        if feats or i % subsample == 0:
            feats = features.wav2features(data, settings.hop_size)
        else:
            feats = lfeats
        if record:
            record.append(feats)

    signals = get_signals(feats)
    del signals['features']
    signals['logmel'] = list(feats.logmel)
    signals['mfccs'] = list(feats.mfccs)
    lfeats = feats
    i += 1

    network.send(settings.integrator_sig_port, signals)
    if settings.timetracing:
        tt()
    status_sender.send('running', settings.status_address)

    data = network.get_json(sock, None)
    if data is None:
        continue
    action = data.get('action', '')
    if action.startswith('subsample='):
        subsample = int(action[len('subsample='):])
        logger.info('subsample=%d', subsample)
    rec_action = data.get('rec_action', '')
    if rec_action:
        logger.info('rec_action=%s', rec_action)

    if rec_action.startswith('start='):
        if record:
            record.close()
            logger.info('finished recording because starting another')
        ident = rec_action[len('start='):]
        record = recording.SoundRecording.create(ident)
        logger.info('recording %r path=%s', record, record.path)
        playback = None
        input_streamer.freeze(False)

    if rec_action == 'stop':
        if record:
            record.close()
            logger.info('finished recording')
        record = playback = None
        input_streamer.freeze(False)

    if rec_action.startswith('play='):
        if record:
            record.close()
            logger.info('finished recording because starting playback')
        ident = rec_action[len('play='):]
        try:
            playback = recording.SoundRecording.load(ident)
        except FileNotFoundError as e:
            logger.warning('Cannot playback: %s', e)
            continue
        logger.info('loaded %r path=%s', playback, playback.path)
        input_streamer.freeze(True)

    if rec_action.startswith('t=') and playback is not None:
        t = float(rec_action[len('t='):])
        playback.seek(t)

del input_streamer
del ai0

print('\nPERF STATS:')
print(perf.stats())

status_sender.send('done')
