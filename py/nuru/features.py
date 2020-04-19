
import collections

import numpy as np  # type: ignore
import scipy.fftpack  # type: ignore

from audioset import vggish_params, mel_features
from smanmi import perf
from . import settings


# wav is expected in float format
Features = collections.namedtuple('Features', [
    'wav', 'logmel', 'logmel2', 'mfccs'])


def log_mel_spectrogram(data,
                        audio_sample_rate=settings.rate,
                        num_mel_bins=settings.num_mel_bins,
                        lower_edge_hertz=settings.lower_edge_hertz,
                        upper_edge_hertz=settings.upper_edge_hertz,
                        window_length_secs=settings.buf_secs,
                        hop_length_secs=settings.hop_secs):
    return mel_features.log_mel_spectrogram(
        data=data,
        audio_sample_rate=audio_sample_rate,
        log_offset=vggish_params.LOG_OFFSET,
        window_length_secs=window_length_secs,
        hop_length_secs=hop_length_secs,
        num_mel_bins=num_mel_bins,
        lower_edge_hertz=lower_edge_hertz,
        upper_edge_hertz=upper_edge_hertz
    )


def log_mel_spectrogram2(data):
    return log_mel_spectrogram(data, num_mel_bins=settings.num_mel_bins2)


def mfccs(data, logmel=None, num_ceps=12, **kwargs):
    if logmel is None:
        logmel = log_mel_spectrogram(data, **kwargs)
    mfcc = scipy.fftpack.dct(logmel, type=2, axis=1, norm='ortho')
    return mfcc[:, 1: (num_ceps + 1)]


assert 2 ** int(np.log(settings.buf_size) / np.log(2)) == settings.buf_size, (
    f'settings.buf_size={settings.buf_size} is not a power of 2')

hann_window = mel_features.periodic_hann(settings.buf_size)
mel_matrix = mel_features.spectrogram_to_mel_matrix(
    num_mel_bins=settings.num_mel_bins,
    num_spectrogram_bins=settings.buf_size // 2 + 1,
    audio_sample_rate=settings.rate,
    lower_edge_hertz=settings.lower_edge_hertz,
    upper_edge_hertz=settings.upper_edge_hertz
)


@perf.measure('wav2features')
def wav2features(wav, hop_size):
    """Calculates audio features.

    Args:
      wav: ndarray of type float
    """
    assert wav.dtype == np.float32, wav.dtype
    assert len(wav) == settings.buf_size, len(wav)
    spectrogram = np.abs(np.fft.rfft(hann_window * wav))
    logmel = np.log(spectrogram.reshape((1, -1)).dot(mel_matrix))
    return Features(
        wav=wav[:hop_size],
        logmel=logmel[0],
        # logmel2=log_mel_spectrogram2(wav)[0],
        logmel2=0,
        mfccs=mfccs(wav, logmel)[0],
    )


@perf.measure('wav2features_old')
def wav2features_old(wav, hop_size):
    """Less efficient original implementation of wav2features.

    This original implementation used the `log_mel_spectrogram()` provided
    in `audioset.mel_features` that is actually a FFTST suitable to computing
    the FFT over multiple frames.
    """
    assert wav.dtype == np.float32, wav.dtype
    logmel = log_mel_spectrogram(wav)
    return Features(
        wav=wav[:hop_size],
        logmel=logmel[0],
        # logmel2=log_mel_spectrogram2(wav)[0],
        logmel2=0,
        mfccs=mfccs(wav, logmel)[0],
    )
