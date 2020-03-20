"""Records audio & extracts FFT."""


import logging, os, signal as pysig, time

import numpy as np  # type: ignore

from smanmi import audio, hotplug, network, perf, util
from . import features, recording, settings


assert os.path.isdir(settings.recorder_dir), (
    'recorder_dir="%s" not found' % settings.recorder_dir)

logger = util.createLogger('recorder')
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
            data16 = settings.in_channels_comination(data16l, data16r)
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
        return features.wav2features(self.data, settings.hop_size)

    def get_dt(self):
        return time.time() - self.t0 - self.t

    def reset_audio_interface(self, audio_interface):
        self.audio_interface = audio_interface
        self.player.reset_audio_interface(audio_interface)


i = 0
i_o = 0

logger.info('Using in_channels={}'.format(settings.in_channels))
audio.init(settings)
ai0 = audio.AudioInterface(
    input=settings.in_channels, output=1)
input_streamer = InputStreamer(ai0)
last_reset_t = time.time()

status_sender = network.StatusSender(name='recorder', logger=logger)

sock = network.create_udp_socket(settings.recorder_cmd_port, settings.address)
loop = False
record = playback = None
while running:

    if (settings.reset_secs
            and time.time() - last_reset_t > settings.reset_secs):
        logger.info('Re-initializing input_streamer.')
        del ai0
        ai0 = audio.AudioInterface(input=1)
        input_streamer.reset_audio_interface(ai0)
        last_reset_t = time.time()

    data = network.get_json(sock, None)
    if data and 'recorder' in data:
        data = data['recorder']
        logger.info('RECEIVED %s', data)
        loop = data.get('loop', loop)
        if 'playback' in data:
            if data['playback']:
                if record:
                    record.close()
                    record = None
                input_streamer.freeze(True)
                playback = recording.Recording.from_name(data['playback'])
                logger.info('loaded %r path=%s', playback, playback.path)
            else:
                input_streamer.freeze(False)
        if 'record' in data:
            if data['record']:
                record = recording.Recording.from_name(data['record'])
                logger.info('recording %r path=%s', record, record.path)
                playback = None
                input_streamer.freeze(False)
            else:
                if record:
                    record.close()
                    logger.info('finished recording')
                record = None
        if playback and 't' in data:
            playback.seek(data['t'])

    feats = None
    if playback:
        feats = playback.read(loop=loop)
        if feats:
            ai0.play(feats.wav)
        else:
            playback = None
            input_streamer.freeze(False)
    if not feats:
        feats = input_streamer.get()
        if record:
            record.append(feats)

    signals = hp_signals.audio_runner(features=feats)
    if playback:
        signals['t'] = playback.t
    del signals['features']
    signals['logmel'] = list(feats.logmel)
    signals['mfccs'] = list(feats.mfccs)
    i += 1

    network.send(settings.integrator_sig_port, signals)
    if settings.timetracing:
        tt()
    status_sender.send('running', settings.address)


del input_streamer
del ai0

print('\nPERF STATS:')
print(perf.stats())

status_sender.send('done')
