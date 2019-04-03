
import argparse, collections, curses, json, logging, os, signal, socket, sys, time

import numpy as np
import pyaudio
import scipy.io.wavfile

import detector, features, util


ALIVE_PATH = 'alive/ongoing.json'

parser = argparse.ArgumentParser(description='Records audio and transforms the signal.')
parser.add_argument('--debug', type=bool, default=False,
        help='Whether debug output should be generated.')

parser.add_argument('--monitor_freq', type=float, default=10.,
        help='Monitor update frequency.')
parser.add_argument('--overdrive_threshold', type=float, default=.02,
        help='Consider overdrive if avg(is_overdrive)>threshold.')
parser.add_argument('--alive_secs', type=float, default=10.,
        help='How often to store "{}".'.format(ALIVE_PATH))

parser.add_argument('--lighter_port', type=int, default=5618,
        help='Which port "lighter" is listening on.')
parser.add_argument('--monitor_port', type=int, default=23918,
        help='Which port "monitor" is listening on.')
parser.add_argument('--address', type=str, default='localhost',
        help='Which address "lighter" and "monitor" are listening on.')
parser.add_argument('--detector1_model', type=str, default='../models/detector1',
        help='Path to saved model of detector1 model. Empty string disables ML.')

parser.add_argument('--output_dir', type=str, default='recordings',
        help='Where to store recorded .json/.wav files. Empty string disables storing of audio.')

args = parser.parse_args()

assert not args.output_dir or os.path.isdir(args.output_dir), (
        'output_dir="%s" not found' % args.output_dir)

logger = util.createLogger('recorder')
if args.debug: logger.setLevel(logging.DEBUG)


running = True

def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False
signal.signal(signal.SIGINT, signal_handler)


class Audio(object):

    #RATE = 44100
    RATE = 16000
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

    def __init__(self, window_secs):
        self.window_secs = window_secs
        self.window_samples = int(self.RATE * window_secs)

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.window_samples)

        self.t = 0
        self.t0 = time.time()

    def read(self, samples):
        data = self.stream.read(samples, exception_on_overflow=False)
        data = np.fromstring(data, np.int16)
        data = util.int16_to_float(data)
        self.t += float(len(data)) / self.RATE
        return data

    def get(self):
        data = self.read(self.window_samples)
        logmel = features.log_mel_spectrogram(
                data, audio_sample_rate=self.RATE,
                window_length_secs=self.window_secs,
                hop_length_secs=self.window_secs)
        ceps = features.mfccs(data, logmel=logmel)
        assert logmel.shape[0] == 1
        assert ceps.shape[0] == 1
        return data, ceps[0], logmel[0]

    def get_dt(self):
        return time.time() - self.t0 - self.t

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


def timestamp():
    return time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))


def store(data, keeper_stats):
    t0 = time.time()
    ts = timestamp()
    base = os.path.join(args.output_dir, ts)
    scipy.io.wavfile.write(base + '.wav', audio.RATE, util.float_to_int16(data))
    secs = 1. * len(data) / audio.RATE
    with open(base + '.json', 'w') as f:
        json.dump({
                'secs': secs,
                'max': data.max(),
                'E_mean': (data**2).mean(),
                'keeper_stats': keeper_stats,
            }, f)
    msg = 'stored %.1fs -> %s in %.1f ms' % (
            secs, base, 1e3*(time.time() - t0))
    logger.info(msg)
    return msg


is_over = lambda x : (x > .99) | (x < -.99)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
monitor_address = (args.address, args.monitor_port)
lighter_address = (args.address, args.lighter_port)

i = 0
i_o = 0

last_alive = 0
stats = dict(started=0, recorded=0)
if os.path.exists(ALIVE_PATH):
    dst = os.path.join( os.path.dirname(ALIVE_PATH), timestamp() + '.json')
    os.rename(ALIVE_PATH, dst)

keeper_kw = dict(logger=logger)
if args.detector1_model:
    import detector1  # Don't import TF if not needed.
    logger.info('Loading TF model "%s"', args.detector1_model)
    keeper_kw['detector'] = detector.detector1_adaptor(
            detector1.Detector1(args.detector1_model))
keeper = detector.Keeper(**keeper_kw)

logger.info('Start recording.')
audio = Audio(window_secs=1./args.monitor_freq)

started = False
think_t0 = None
while running:
    t0 = time.time()
    data, ceps, logmel = audio.get()
    intensity = ceps.max()
    i += 1
    overdrive = bool(is_over(data).mean() > args.overdrive_threshold)
    i_o += overdrive

    if args.alive_secs and (i - last_alive)/args.monitor_freq > args.alive_secs:
        stats['ts'] = timestamp()
        stats['i'] = i
        stats['i_o'] = i_o
        with open(ALIVE_PATH, 'w') as f:
            json.dump(stats, f)
        last_alive = i

    monitor_message = {
            'mel': list(ceps),
            'loudness': intensity,
            'keeper': keeper.lastdbg(),
            }
    lighter_message = {}
    if overdrive:
        lighter_message['overdrive'] = True

    if keeper.add(data, ceps, logmel) and args.output_dir:
        stats['recorded'] += 1
        msg = store(np.concatenate(keeper.bufs.data.as_list()), keeper.stats())
        monitor_message['msg'] = msg
        lighter_message['state'] = 'search'
        started = False
    elif len(keeper.bufs.data) == 10:
        stats['started'] += 1
        logger.info('len(keeper.data) == 10 - start')
        lighter_message['state'] = 'start'
        started = True
    elif started and keeper.state == keeper.BELOW:
        lighter_message['state'] = 'wait'
        started = False

    monitor_message = json.dumps(monitor_message).encode('utf8')
    sock.sendto(monitor_message, monitor_address)

    lighter_message = json.dumps(lighter_message).encode('utf8')
    sock.sendto(lighter_message, lighter_address)

logger.info('Stop recording.')
audio.stop()

