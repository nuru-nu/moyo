
import collections

import scipy.fftpack

from audioset import vggish_params, mel_features
import perf, settings


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


@perf.measure('wav2features')
def wav2features(wav):
    logmel = log_mel_spectrogram(wav)
    return Features(
        wav=wav,
        logmel=logmel[0],
        # logmel2=log_mel_spectrogram2(wav)[0],
        logmel2=0,
        mfccs=mfccs(wav, logmel)[0],
    )
