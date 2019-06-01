"""Records audio, generates features and sends messages."""

import argparse, json, logging, os, signal as pysig, socket, time, wave

import numpy as np
import scipy.io.wavfile

import audio, features, hotplug, network, perf, settings, state, util


ALIVE_PATH = 'alive/ongoing.json'
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../recordings/recorder2')

parser = argparse.ArgumentParser(
    description='Records audio and transforms the signal.')
parser.add_argument('--debug', type=bool, default=False,
                    help='Whether debug output should be generated.')

parser.add_argument('--output_dir', type=str, default=OUTPUT_DIR,
                    help='Where to store recorded .json/.wav files. '
                    'Empty string disables storing of audio.')

parser.add_argument('--reset_secs', type=int, default=0,
                    help='If this parameter is >0, then the audio interface '
                    'is HARD RESET every this many seconds. This was observed '
                    'to avoid delay creep on certain configurations '
                    '(especially after the system is unfrozen).')

parser.add_argument('--monitor_address', type=str, default=settings.address,
                    help='IP address to which to send monitor UDP data.')

args = parser.parse_args()

assert not args.output_dir or os.path.isdir(args.output_dir), (
    'output_dir="%s" not found' % args.output_dir)

logger = util.createLogger('recorder')
if args.debug:
    logger.setLevel(logging.DEBUG)

hp = hotplug.HotPlug(logger, modules=('signals',))

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
    def read(self, samples, signals):
        data = self.audio_interface.input_stream.read(
            samples, exception_on_overflow=False)
        data16 = np.frombuffer(data, settings.dtype_np)
        data = util.int16_to_float(data16)
        data = hp.signals.microphone_effect(data, signals)
        self.t += float(len(data)) / settings.rate
        if self.wav_path and self.wav:
            self.wav.writeframesraw(data16)
        return data

    def clear_buffers(self):
        while self.audio_interface.input_stream.get_read_available():
            n = self.audio_interface.input_stream.read(
                self.audio_interface.input_stream.get_read_available())
            logger.info('Clearing buffers : read n={} bytes.'.format(n))

    def get(self, signals):
        self.data = np.roll(self.data, shift=-settings.hop_size, axis=0)
        self.data[-settings.hop_size:] = self.read(settings.hop_size, signals)
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


@perf.measure('get_signals')
def get_signals(feats, signalin, state):
    signals = hp.signals.runner(
        features=feats, t=time.time(), signalin=signalin, state=state)
    signals['mfccs'] = feats.mfccs
    signals['logmel'] = feats.logmel
    del signals['features']
    return signals


@perf.measure('send_signals')
def send_signals(data):
    msg = util.pythonize(data)
    msg = json.dumps(msg).encode('utf8')
    sock.sendto(msg, (args.monitor_address, settings.monitor_port))
    sock.sendto(msg, (settings.address, settings.player_port))
    sock.sendto(msg, (settings.address, settings.player2_port))
    sock.sendto(msg, (settings.address, settings.fadecandy_port))
    sock.sendto(msg, (settings.address, settings.dmx_port))


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
signalin_sock = network.create_udp_socket(settings.signalin_port)

i = 0
i_o = 0

last_alive = 0
stats = dict(started=0, recorded=0)
if os.path.exists(ALIVE_PATH):
    dst = os.path.join(os.path.dirname(ALIVE_PATH), timestamp() + '.json')
    os.rename(ALIVE_PATH, dst)

logger.info('Start recording.')
ai0 = audio.AudioInterface(input=1)
input_streamer = InputStreamer(ai0, output_dir=args.output_dir)
last_reset_t = time.time()

started = False
think_t0 = None
frozen = 0
logmel_src = 'input'
signals = dict(state=state.State())
while running:

    signalin = network.get_json(signalin_sock, {})

    new_frozen = signals['state'].state == 'frozen'
    if new_frozen and signalin.get('newstate', 'frozen') != 'frozen':
        # Must do this so when state changes the input_stream will be started.
        new_frozen = False
    if frozen != new_frozen:
        frozen = new_frozen
        input_streamer.freeze(frozen)
        if not frozen and args.reset_secs > 0:
            last_reset_t = 0  # Force reset (if enabled) after unfreeze.
    if frozen and 'newstate' not in signalin:
        time.sleep(settings.hop_secs)
        continue

    if args.reset_secs and time.time() - last_reset_t > args.reset_secs:
        logger.info('Re-initializing input_streamer after freeze.')
        del ai0
        ai0 = audio.AudioInterface(input=1)
        input_streamer.reset_audio_interface(ai0)
        last_reset_t = time.time()

    feats = input_streamer.get(signals)
    i += 1

    if settings.alive_secs and (
            i - last_alive) * settings.hop_secs > settings.alive_secs:
        stats['ts'] = timestamp()
        stats['i'] = i
        stats['i_o'] = i_o
        with open(ALIVE_PATH, 'w') as f:
            json.dump(stats, f)
        last_alive = i

    signals = get_signals(feats, signalin, state=signals['state'])
    logmel_src = signalin.get('logmel_src', logmel_src)
    if logmel_src.startswith('output'):
        channel = int(logmel_src[-1])
        signals['logmel'] = features.wav2features(
            hp.effects.effector.bufs[channel].buf).logmel

    send_signals(signals)


logger.info('Stop recording.')
del input_streamer
del ai0

print('\nPERF STATS:')
print(perf.stats())
