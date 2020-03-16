"""Records audio & extracts FFT."""


import logging, os, signal as pysig, time, wave

import numpy as np

from smanmi import audio, hotplug, network, perf, util
from . import features, settings


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

    def __init__(self, audio_interface, output_dir=None):
        self.audio_interface = audio_interface

        # will be initialized when .freeze(false) is called the first time
        self.wav = self.wav_path = None
        self.t = 0
        self.t0 = time.time()
        self.data = np.zeros(settings.buf_size, dtype=np.float32)
        self.output_dir = output_dir

    def freeze(self, frozen):
        if frozen:
            logger.info('...stop recording {}'.format(self.wav_path))
            self.audio_interface.input_stream.stop_stream()
            self.close()
        else:
            if self.output_dir:
                now = int(time.time())
                self.wav_path = os.path.join(
                    self.output_dir, '{}.wav'.format(now))
                logger.info('start recording {}...'.format(self.wav_path))
                self.wav = wave.open(self.wav_path, 'wb')
                self.wav.setnchannels(1)
                self.wav.setframerate(settings.rate)
                self.wav.setsampwidth(settings.sampwidth)
            self.audio_interface.input_stream.start_stream()

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
        if self.wav_path and self.wav:
            self.wav.writeframesraw(data16)
        return data

    def clear_buffers(self):
        while self.audio_interface.input_stream.get_read_available():
            n = self.audio_interface.input_stream.read(
                self.audio_interface.input_stream.get_read_available())
            logger.info('Clearing buffers : read n={} bytes.'.format(n))

    def get(self):
        self.data = np.roll(self.data, shift=-settings.hop_size, axis=0)
        self.data[-settings.hop_size:] = self.read(settings.hop_size)
        return features.wav2features(self.data)

    def get_dt(self):
        return time.time() - self.t0 - self.t

    def close(self):
        if self.wav:
            logger.info('Recorded {} seconds to {}'.format(
                int(self.t), self.wav_path))
            self.wav.close()
            self.wav = None

    def reset_audio_interface(self, audio_interface):
        self.audio_interface = audio_interface
        self.player.reset_audio_interface(audio_interface)

    def __del__(self):
        self.close()


i = 0
i_o = 0

logger.info('Start recording.')
logger.info('Using in_channels={}'.format(settings.in_channels))
audio.init(settings)
ai0 = audio.AudioInterface(input=settings.in_channels)
input_streamer = InputStreamer(ai0, output_dir=settings.recorder_dir)
last_reset_t = time.time()

status_sender = network.StatusSender(name='recorder', logger=logger)

while running:

    if (settings.reset_secs
            and time.time() - last_reset_t > settings.reset_secs):
        logger.info('Re-initializing input_streamer.')
        del ai0
        ai0 = audio.AudioInterface(input=1)
        input_streamer.reset_audio_interface(ai0)
        last_reset_t = time.time()

    feats = input_streamer.get()
    signals = hp_signals.audio_runner(features=feats)
    del signals['features']
    signals['logmel'] = list(feats.logmel)
    signals['mfccs'] = list(feats.mfccs)
    i += 1

    network.send(settings.integrator_sig_port, signals)
    if settings.timetracing:
        tt()
    status_sender.send('running', settings.address)


logger.info('Stop recording.')
del input_streamer
del ai0

print('\nPERF STATS:')
print(perf.stats())

status_sender.send('done')
