"""Utilities for managing audio recordings."""

import datetime
import glob
import json
import os
import pickle
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import wave

import numpy as np  # type: ignore

from smanmi import util
from .features import Features, wav2features
from . import settings
from .settings import AudioSettings


class Recording:
    """Streams signals with 't' from/to disk.
    
    Stored with basepath={settings.rec_dir}/{YYYYMMDD_HHSS}
    {basepath}.ndjson : stream of signals
    {basepath}.json : meta info
    """
    @classmethod
    def load(cls, identifier: str) -> Optional['Recording']:
        basepath = f'{settings.recs_dir}/{identifier}'
        if os.path.exists(f'{basepath}.ndjson'):
            rec = cls(basepath)
            if rec.info['length']:
                return rec
        return None

    @classmethod
    def create(cls, ident) -> 'Recording':
        basepath = f'{settings.recs_dir}/{ident}'
        rec = cls(basepath)
        assert not rec.reading, rec.basepath
        return rec

    @classmethod
    def read_recs(cls) -> List[Dict[str, Any]]:
        infos = []
        for path in glob.glob(f'{settings.recs_dir}/*.json'):
            ndjson_path = '.'.join(path.split('.')[:-1] + ['ndjson'])
            if os.path.exists(ndjson_path):
                with open(path, encoding='utf8') as f:
                    info = json.load(f)
                    if info['length']:
                        infos.append(info)
        infos.sort(key=lambda info: -info['start'])
        return infos

    def __init__(self, basepath: str):
        self.basepath = basepath
        self.ndjsonpath = f'{basepath}.ndjson'
        self.jsonpath = f'{basepath}.json'
        if os.path.exists(self.ndjsonpath):
            self.reading = True
            # Note: cannot do nonzero end-relative seek() with encoding.
            self.loadinfo()
            self.fin = open(self.ndjsonpath, 'rb')
        else:
            self.reading = False
            self.fout = open(self.ndjsonpath, 'w', encoding='utf8')
            self.info : Dict[str, Any] = dict(
                id=os.path.basename(self.basepath),
                name='',
                comments='',
                signals=[],
                length=0,
                start=None,
                stop=None,
            )
            self.signals: Set[str] = set()
            self.saveinfo()
            self.lastsignals : Dict[str, Any] = {}

    def close(self):
        assert not self.reading, self.basepath
        self.saveinfo()
        self.fout.close()

    def saveinfo(self):
        with open(self.jsonpath, 'w', encoding='utf8') as f:
            json.dump(self.info, f, indent=2)

    def loadinfo(self):
        with open(self.jsonpath, encoding='utf8') as f:
            self.info = json.load(f)

    def write(self, signals: Dict[str, Any], transients: Iterable[str]):
        assert not self.reading, self.basepath
        signals = {
            name: signal
            for name, signal in signals.items() if name != 't' and (
                name in transients or signal != self.lastsignals.get(name))
        }
        if not signals:
            return
        t = time.time()
        signals = dict(t=t, **signals)
        newsigs = set(signals).difference('t').difference(self.signals)
        if newsigs:
            self.signals = self.signals.union(newsigs)
            self.info['signals'] = sorted(list(self.signals))
            self.saveinfo()
        if self.info['start'] is None:
            self.info['start'] = t
        if self.info['stop'] is not None:
            assert self.info['stop'] <= t, (self.basepath, self.info['stop'],
                                            signals['t'])
        self.info['stop'] = t
        assert not self.reading, self.basepath
        line = json.dumps(signals) + '\n'
        self.fout.write(line)
        self.info['length'] += len(line)
        self.lastsignals.update(signals)

    def restart(self):
        self.fin.seek(0)

    def next(self) -> Dict[str, Any]:
        assert self.reading, self.basepath
        line = self.fin.readline().decode('utf8')
        if not line:
            raise StopIteration
        return json.loads(line)

    def _readat(self,
                pos: int,
                backoff: int = 100) -> Tuple[int, Dict[str, Any]]:
        while True:
            self.fin.seek(pos)
            pos_corrected = pos
            buf = self.fin.readline()
            if buf:
                pos_corrected += len(buf)
                buf = self.fin.readline()
                if buf:
                    return pos_corrected, json.loads(buf.decode('utf8'))
            pos -= backoff

    def seek(self, t: float):
        assert self.reading, self.basepath
        at, bt = self.info['start'], self.info['stop']
        assert at <= t <= bt, (at, t, bt)
        apos, bpos = 0, self.info['length']
        while True:
            pos = int((apos + bpos) / 2)
            pos, signals = self._readat(pos)
            if t < signals['t']:
                if bpos == pos:
                    break
                bt, bpos = signals['t'], pos
            else:
                if apos == pos:
                    break
                at, apos = signals['t'], pos
        # should search binarily here ... but we don't really need the precision
        self.fin.seek(pos)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self.basepath})'


class SoundRecording:
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
    def __init__(self,
                 path: str,
                 audio: AudioSettings = settings.audio,
                 *,
                 create_ok: bool = True):
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
            if not create_ok:
                raise FileNotFoundError(f'Does not exist: "{path}"')
            self._open()

    @classmethod
    def create(cls,
               ident: str,
               audio: AudioSettings = settings.audio) -> 'SoundRecording':
        path = f'{settings.recs_dir}/{ident}.wav'
        return cls(path, audio, create_ok=True)

    @classmethod
    def load(cls,
             ident: str,
             audio: AudioSettings = settings.audio) -> 'SoundRecording':
        path = f'{settings.recs_dir}/{ident}.wav'
        return cls(path, audio, create_ok=False)

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
        print('seek', self.i)
        self.i = max(0,
                     min(len(self.logmel) - 1, int(t / self.audio.hop_secs)))
        self.wav.setpos(self.i * self.audio.hop_size)
        print('->', self.i)

    def read(self, loop: bool = False) -> Optional[Features]:
        if self.i >= len(self.logmel):
            if not loop:
                return None
            self.i = 0
            self.wav.rewind()
        wav = self.wav.readframes(self.audio.hop_size)
        wav = np.frombuffer(wav, self.audio.dtype_np)
        wav = util.int16_to_float(wav)
        features = Features(wav=wav,
                            logmel=self.logmel[self.i],
                            mfccs=self.mfccs[self.i],
                            logmel2=None)
        self.i += 1
        return features

    def envelope(self, length):
        """Returns an envelope suitable for overview display."""
        n = self.logmel.shape[0]
        d = max(1, n / length)
        arr = np.array([
            self.logmel[int(i):int(i + d)].mean()
            for i in np.linspace(0, n, int(length), endpoint=False)
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


def get_recordings(directory: str = settings.recorder_dir):
    """Returns a list of `SoundRecording`, fails if any cannot be read."""
    return [
        SoundRecording(path)
        for path in glob.glob(os.path.join(directory, '*.wav'))
    ]


def convert(path_in, path_out, audio=settings.audio):
    """Converts a pure WAV recording to a `SoundRecording` recording."""
    wav = wave.open(path_in, 'rb')
    assert wav.getnchannels() == 1, wav.getnchannels()
    assert wav.getframerate() == audio.rate, wav.getframerate()
    assert wav.getsampwidth() == audio.sampwidth, wav.getsampwidth()
    rec = SoundRecording(path_out, audio)
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
