"""Records audio, generates features and sends messages.

Example invocation using a detector model:

    python recorder2.py
        --detector_model=../data/models/tmo_wp_10_10_linear.h5
        --preprocessor=wp_10_10
"""

import argparse, io, json, logging, os, signal, socket, time

import aubio
import numpy as np
import scipy.io.wavfile

import audio, config, features, settings, streaming, util


ALIVE_PATH = 'alive/ongoing.json'
PREPROCESSORS = {
    'none': lambda x: x,
    'wp_5_5': streaming.WithPrevious(n=5, d=5),
    'wp_10_10': streaming.WithPrevious(n=10, d=10),
}

parser = argparse.ArgumentParser(
    description='Records audio and transforms the signal.')
parser.add_argument('--debug', type=bool, default=False,
                    help='Whether debug output should be generated.')

parser.add_argument('--overdrive_threshold', type=float, default=.02,
                    help='Consider overdrive if avg(is_overdrive)>threshold.')
parser.add_argument('--alive_secs', type=float, default=10.,
                    help='How often to store "{}".'.format(ALIVE_PATH))

parser.add_argument('--listen_address', type=str, default=settings.address,
                    help='Which address to listen on.')
parser.add_argument('--port', type=int, default=settings.recorder_port,
                    help='Which port to listen on.')
parser.add_argument('--lighter_port', type=int, default=settings.lighter_port,
                    help='Which port "lighter" is listening on.')
parser.add_argument('--monitor_port', type=int, default=settings.monitor_port,
                    help='Which port "monitor" is listening on.')
parser.add_argument('--address', type=str, default=settings.address,
                    help='Which address to send to.')

parser.add_argument('--detector_model', type=str, default='',
                    help='Path to Keras detector model.'
                    'Empty string disables ML.')
parser.add_argument('--preprocessor', type=str, default='none',
                    choices=PREPROCESSORS.keys(),
                    help='What preprocessor to use.')

parser.add_argument('--output_dir', type=str, default='',
                    help='Where to store recorded .json/.wav files. '
                    'Empty string disables storing of audio.')

args = parser.parse_args()

assert not args.output_dir or os.path.isdir(args.output_dir), (
    'output_dir="%s" not found' % args.output_dir)

logger = util.createLogger('recorder')
if args.debug:
    logger.setLevel(logging.DEBUG)

conf = config.Config(logger)

running = True


def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False


signal.signal(signal.SIGINT, signal_handler)


class Player:

    def __init__(self, audio_interface):
        self.data = {}
        t0 = time.time()
        for name, path in settings.get_recordings().items():
            sr, data = scipy.io.wavfile.read(path)
            if sr != settings.rate:
                logger.warning('IGNORING {} {}!={}'.format(
                    name, sr, settings.rate))
                continue
            if data.dtype != settings.dtype_np:
                logger.warning('IGNORING {} {}!={}'.format(
                    name, data.dtype.name, settings.dtype_np.name))
                continue
            self.data[name] = data
        logger.info('Loaded {} recordings in {:.3f}ms'.format(
            len(self.data), time.time() - t0))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0)
        self.sock.bind((args.listen_address, args.port))

        self.audio_interface = audio_interface

        self.stop()

    def stop(self):
        self.name = self.bufi = self.t0 = None

    def playing(self):
        try:
            data, address = self.sock.recvfrom(4096)
            try:
                data = json.loads(data.decode('utf8'))
                if 'play' in data:
                    self.name = data['play']
                    self.bufi = 0
                    self.t0 = time.time()
                    logger.info('Will play {}'.format(self.name))
            except json.JSONDecodeError as e:
                logger.warning('Could not decode {!r} : {}'.format(data, e))
        except io.BlockingIOError:
            pass
        return self.name

    def get(self, samples):
        buf = np.zeros(shape=samples, dtype=settings.dtype_np)
        if self.name:
            data = self.data[self.name]
            n = min(samples, len(data) - self.bufi)
            buf[:n] = data[self.bufi: self.bufi + n]
            self.bufi += n
            self.audio_interface.output_stream.write(buf.tostring())
            # dt = time.time() - t0
            # if dt < samples / settings.rate:
            #     time.sleep(samples / settings.rate - dt)
            self.t0 = time.time()
            if self.bufi >= len(data):
                self.stop()
        return buf


class InputStreamer(object):

    def __init__(self, audio_interface):
        self.player = Player(audio_interface)
        self.audio_interface = audio_interface

        self.pitcher = aubio.pitch(method='yinfft',
                                   buf_size=settings.buf_size,
                                   hop_size=settings.hop_size,
                                   samplerate=settings.rate)
        self.pitcher.set_unit('Hz')
        self.outlier_filter = streaming.OutlierFilter(d=100, n=2)
        self.envelop_averager = streaming.EnvelopAverager(
            buf_size=settings.buf_size, n=10)

        self.t = 0
        self.t0 = time.time()
        self.data = np.zeros(settings.buf_size, dtype=np.float32)

    def read(self, samples):
        if self.player.playing():
            data = self.player.get(samples)
        else:
            data = self.audio_interface.input_stream.read(
                samples, exception_on_overflow=False)
            data = np.frombuffer(data, np.int16)
        data = util.int16_to_float(data)
        self.t += float(len(data)) / settings.rate
        return data

    def hop_over(self):
        self.read(settings.hop_size)

    def get(self):
        self.data = np.roll(self.data, shift=-settings.hop_size, axis=0)
        self.data[-settings.hop_size:] = self.read(settings.hop_size)

        logmel = features.log_mel_spectrogram(
            self.data, audio_sample_rate=settings.rate,
            window_length_secs=settings.buf_secs,
            hop_length_secs=settings.hop_secs,
            num_mel_bins=settings.num_mel_bins)
        ceps = features.mfccs(self.data, logmel=logmel)
        assert logmel.shape[0] == 1
        assert ceps.shape[0] == 1

        self.pitcher.set_tolerance(conf['pitcher_tolerance'])
        pitch = self.pitcher(self.data[-settings.hop_size:])[0]
        pitch = float(self.outlier_filter(pitch))
        loud = float(self.envelop_averager(self.data)) * conf['loud_scale']

        return self.data, ceps[0], logmel[0], pitch, loud

    def get_dt(self):
        return time.time() - self.t0 - self.t


def timestamp():
    return time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))


def store(data, keeper_stats):
    t0 = time.time()
    ts = timestamp()
    base = os.path.join(args.output_dir, ts)
    scipy.io.wavfile.write(base + '.wav', settings.rate,
                           util.float_to_int16(data))
    secs = 1. * len(data) / settings.rate
    with open(base + '.json', 'w') as f:
        json.dump({
            'secs': secs,
            'max': data.max(),
            'E_mean': (data**2).mean(),
            'keeper_stats': keeper_stats,
        }, f)
    msg = 'stored %.1fs -> %s in %.1f ms' % (
        secs, base, 1e3 * (time.time() - t0))
    logger.info(msg)
    return msg


def is_over(x):
    return (x > .99) | (x < -.99)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
monitor_address = (args.address, args.monitor_port)
fadecandy_address = (args.address, settings.fadecandy_port)
lighter_address = (args.address, args.lighter_port)

i = 0
i_o = 0

last_alive = 0
stats = dict(started=0, recorded=0)
if os.path.exists(ALIVE_PATH):
    dst = os.path.join(os.path.dirname(ALIVE_PATH), timestamp() + '.json')
    os.rename(ALIVE_PATH, dst)

keeper_kw = dict(logger=logger)
detectors = {}
if args.detector_model:
    logger.info('Importing TensorFlow')
    import tensorflow as tf
    logger.info('Loading TF model "%s"', args.detector_model)
    model = tf.keras.models.load_model(args.detector_model)
    detectors['tf'] = streaming.KerasDetector(
        model, PREPROCESSORS[args.preprocessor])
    detectors['m4'] = streaming.MedianFilter(detectors['tf'], n=4)
    detectors['m10'] = streaming.MedianFilter(detectors['tf'], n=10)
    detectors['m10.7'] = streaming.MedianFilter(
        detectors['tf'], n=10, threshold=0.7)
# keeper = detector.Keeper(**keeper_kw)

logger.info('Start recording.')
audio_interface = audio.AudioInterface(input=True, output=True)
input_streamer = InputStreamer(audio_interface)

started = False
think_t0 = None
while running:
    if conf['frozen']:
        input_streamer.hop_over()
        continue
    t0 = time.time()
    data, ceps, logmel, pitch, loud = input_streamer.get()

    intensity = ceps.max()
    i += 1
    overdrive = bool(is_over(data).mean() > args.overdrive_threshold)
    i_o += overdrive

    if args.alive_secs and (
            i - last_alive) * settings.hop_secs > args.alive_secs:
        stats['ts'] = timestamp()
        stats['i'] = i
        stats['i_o'] = i_o
        with open(ALIVE_PATH, 'w') as f:
            json.dump(stats, f)
        last_alive = i

    monitor_message = {
        'mel': list(ceps),
        'logmel': list(logmel),
        'loudness': intensity,
        # 'keeper': keeper.lastdbg(),
        'pitch': pitch,
        'loud': loud,
    }
    for detector_name, detector in detectors.items():
        monitor_message[detector_name] = float(detector(logmel, t=i))
    lighter_message = {}
    if overdrive:
        lighter_message['overdrive'] = True

    # if keeper.add(data, ceps, logmel) and args.output_dir:
    #     stats['recorded'] += 1
    #     msg = store(np.concatenate(keeper.bufs.data.as_list()),
    #                 keeper.stats())
    #     monitor_message['msg'] = msg
    #     lighter_message['state'] = 'search'
    #     started = False
    # elif len(keeper.bufs.data) == 10:
    #     stats['started'] += 1
    #     logger.info('len(keeper.data) == 10 - start')
    #     lighter_message['state'] = 'start'
    #     started = True
    # elif started and keeper.state == keeper.BELOW:
    #     lighter_message['state'] = 'wait'
    #     started = False

    monitor_message = json.dumps(monitor_message).encode('utf8')
    sock.sendto(monitor_message, monitor_address)

    sock.sendto(monitor_message, fadecandy_address)

    lighter_message = json.dumps(lighter_message).encode('utf8')
    sock.sendto(lighter_message, lighter_address)

logger.info('Stop recording.')
del audio_interface
