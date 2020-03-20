"""Utilities for managing audio recordings."""

import glob
import os
import pickle
import re
from typing import List, Optional
import wave

import numpy as np  # type: ignore

from smanmi import util
from .features import Features, wav2features
from . import settings
from .settings import AudioSettings


class Recording:
    """Represents a sound recording.

    Recordings are stored in `settings.recorder_dir` by default with a name
    like "yyyymmdd_HHMMSS_{name}".

    All features are loaded in memory, but the wav data is read in a streaming
    fashion from disk.

    Synopsis:
      from . import recording
      rec = recording.from_name('test')
      for feats in get_audio():
        rec.append(feats)
      rec.close()
      rec2 = recording.Recording.load(rec.path)
      for feats in rec2:
        process(feats)
      plt.plot(rec2.logmel.T)
    """

    def __init__(
            self, path: str, audio: AudioSettings = settings.audio):
        """Creates a new recording.

        If the path exists, then the recording is read (failing if it is not
        compatible with `audio`).

        If the path does not exist, then it is opened for writing.
        """
        assert path[-4:] == '.wav', path
        self.audio = audio
        self.path = path
        self.i = 0
        self.logmel: List[np.array] = []
        self.mfccs: List[np.array] = []  # type: ignore
        if os.path.exists(self.path):
            self._load()
        else:
            self._open()

    @property
    def data_path(self) -> str:
        return f'{self.path[:-4]}.pickle'

    @property
    def name(self):
        return self.path[:-4].split('/')[-1]

    @property
    def t(self) -> float:
        return self.i * self.audio.hop_secs

    @property
    def secs(self) -> float:
        return len(self.logmel) * self.audio.hop_secs

    def _load(self):
        assert os.path.exists(self.path), self.path
        assert os.path.exists(self.data_path), self.data_path
        data = pickle.load(open(self.data_path, 'rb'))
        assert self.audio == data['audio']
        self.logmel = data['logmel']
        self.mfccs = data['mfccs']
        self.wav = wave.open(self.path, 'rb')
        self.writing = False

    def _open(self):
        self.wav = wave.open(self.path, 'wb')
        self.wav.setnchannels(1)
        self.wav.setframerate(self.audio.rate)
        self.wav.setsampwidth(self.audio.sampwidth)
        self.writing = True

    def append(self, features: Features):
        assert self.writing
        assert len(features.wav) == self.audio.hop_size
        data = util.float_to_int16(features.wav)
        self.wav.writeframes(data)
        self.logmel.append(features.logmel)
        self.mfccs.append(features.mfccs)
        self.i += 1

    def close(self):
        self.logmel = np.array(self.logmel)
        self.mfccs = np.array(self.mfccs)
        data = dict(
            logmel=self.logmel,
            mfccs=self.mfccs,
            audio=self.audio,
        )
        pickle.dump(data, open(self.data_path, 'wb'))
        self.wav.close()
        self.i = 0
        self.wav = wave.open(self.path, 'rb')
        self.writing = False

    def seek(self, t: float):
        assert not self.writing
        self.i = max(0, min(len(self.logmel) - 1,
                            int(t / self.audio.hop_secs)))

    def read(self, loop: bool = False) -> Optional[Features]:
        if self.i >= len(self.logmel):
            if not loop:
                return None
            self.i = 0
            self.wav.rewind()
        wav = self.wav.readframes(self.audio.hop_size)
        wav = np.frombuffer(wav, self.audio.dtype_np)
        wav = util.int16_to_float(wav)
        features = Features(
            wav=wav, logmel=self.logmel[self.i], mfccs=self.mfccs[self.i],
            logmel2=None)
        self.i += 1
        return features

    def envelope(self, length):
        """Returns an envelope suitable for overview display."""
        n = self.logmel.shape[0]
        d = max(1, n / length)
        arr = np.array([
            self.logmel[int(i): int(i + d)].mean()
            for i in np.linspace(0, n, length, endpoint=False)
        ])
        return (arr - arr.min())

    def __iter__(self):
        """Shorthand for `read(loop=False)`."""
        feats = self.read()
        while feats:
            yield feats
            feats = self.read()

    def __repr__(self):
        return (f'{self.__class__.__name__}(hops={len(self.logmel)}, '
                f'secs={len(self.logmel)*self.audio.hop_secs:.1f})')

    @classmethod
    def from_name(cls, name, audio: AudioSettings = settings.audio):
        """Helper to construct name with timestamp in recorder dir."""
        if not re.match(r'^\d{8}_\d{6}', name):
            name = f'{util.now()}_{name}'
        return Recording(
            os.path.join(settings.recorder_dir, f'{name}.wav'), audio)


def get_recordings(directory: str = settings.recorder_dir):
    """Returns a list of `Recording`, fails if any cannot be read."""
    return [
        Recording(path)
        for path in glob.glob(os.path.join(directory, '*.wav'))
    ]


def convert(path_in, path_out, audio=settings.audio):
    """Converts a pure WAV recording to a `Recording` recording."""
    wav = wave.open(path_in, 'rb')
    assert wav.getnchannels() == 1, wav.getnchannels()
    assert wav.getframerate() == audio.rate, wav.getframerate()
    assert wav.getsampwidth() == audio.sampwidth, wav.getsampwidth()
    rec = Recording(path_out, audio)
    ldata = None
    while True:
        data = wav.readframes(audio.hop_size)
        data = util.int16_to_float(np.frombuffer(data, audio.dtype_np))
        if len(data) < audio.hop_size:
            break
        if ldata is not None:
            buf = np.concatenate([ldata, data])
            feats = wav2features(buf, audio.hop_size)
            rec.append(feats)
        ldata = data
    rec.close()
    return rec
