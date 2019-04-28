
import numpy as np
import pyaudio

import settings, util


class AudioInterface:
    """Record / play sounds.

    Channels are interleaved sample by sample, e.g.
    LEFT = [1, 2, 3, 4]
    RIGHT = [10, 20, 30, 40]
    => buf=[1, 10, 2, 20, 3, 30, 4, 40]

    Don't forget to convert samples with `util.float_to_int16()` and
    `util.int16_to_float()` when apllying effects...
    """

    CHUNK = 1024

    def __init__(self, input=0, output=0, device_index=None):
        self.p = pyaudio.PyAudio()
        # (for compatibility)
        input = int(input)
        output = int(output)
        if input:
            self.input_stream = self.p.open(
                input_device_index=device_index,
                format=settings.dtype,
                channels=input,
                rate=settings.rate,
                input=True,
                frames_per_buffer=settings.hop_size)
        if output:
            self.output_stream = self.p.open(
                output_device_index=device_index,
                format=settings.dtype,
                channels=output,
                rate=settings.rate,
                output=True,
                frames_per_buffer=settings.hop_size)

    def __del__(self):
        if hasattr(self, 'input_stream'):
            self.input_stream.stop_stream()
            self.input_stream.close()
        if hasattr(self, 'output_stream'):
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.p.terminate()

    def play(self, wav):
        """Plays `wav` (can be float or int16 array) using `settings`."""
        self.output_stream.write(util.float_to_int16(wav).tostring())

    def record(self, secs, print_startstop=True):
        """Records `secs` worth of audio and returns int16 array."""
        # Empty buffer.
        while self.input_stream.get_read_available():
            self.input_stream.read(self.input_stream.get_read_available())
        if print_startstop:
            print("* recording")

        frames = []
        for i in range(0, int(settings.rate / self.CHUNK * secs)):
            data = self.input_stream.read(self.CHUNK)
            frames.append(data)

        if print_startstop:
            print("* done recording")

        return np.concatenate([
            np.fromstring(frame, np.int16) for frame in frames])

    @classmethod
    def list_devices(cls):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            print('device_index={} "{}", input={}, output={} // {}'.format(
                i, dev['name'], dev['maxInputChannels'],
                dev['maxOutputChannels'], None))


def playback(wav):
    """Plays `wav` (can be float or int16 array) using `settings`."""
    audio_interface = AudioInterface(input=False, output=True)
    audio_interface.play(wav)
    del audio_interface


def record(secs, print_startstop=True):
    """Records `secs` worth of audio and returns int16 array."""
    audio_interface = AudioInterface(input=True, output=False)
    data = audio_interface.record(secs, print_startstop=print_startstop)
    del audio_interface
    return data


def tostereo(left, right):
    return np.vstack([
        util.float_to_int16(left),
        util.float_to_int16(right),
    ]).reshape(-1, order='F')


def compress(data, factor):
    # TODO interpol
    return np.arctan(data * factor) / np.pi * 2


if __name__ == '__main__':
    AudioInterface.list_devices()
