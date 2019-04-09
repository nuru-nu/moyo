
import scipy.fftpack

import sys
if 'audioset' not in sys.path: sys.path.append('audioset')
from audioset import vggish_params, mel_features

def log_mel_spectrogram(data,
                        audio_sample_rate=16000,
                        num_mel_bins=64,
                        lower_edge_hertz=125,
                        upper_edge_hertz=7500,
                        window_length_secs=0.1,
                        hop_length_secs=0.1):
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

def mfccs(data, logmel=None, num_ceps=12, **kwargs):
    if logmel is None:
        logmel = log_mel_spectrogram(data, **kwargs)
    mfcc = scipy.fftpack.dct(logmel, type=2, axis=1, norm='ortho')[:, 1 : (num_ceps + 1)] # Keep 2-13
    return mfcc

