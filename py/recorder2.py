"""Records audio, generates features and sends messages."""

import argparse, io, json, logging, os, signal as pysig, socket, time, wave

import numpy as np
import scipy.io.wavfile

import audio, config, features, hotplug, perf, settings, util


ALIVE_PATH = 'alive/ongoing.json'
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../recordings/recorder2')

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
parser.add_argument('--address', type=str, default=settings.address,
                    help='Which address to send to.')

parser.add_argument('--output_dir', type=str, default=OUTPUT_DIR,
                    help='Where to store recorded .json/.wav files. '
                    'Empty string disables storing of audio.')

parser.add_argument('--reset_secs', type=int, default=0,
                    help='If this parameter is >0, then the audio interface is '
                    'HARD RESET every this many seconds. This was observed '
                    'to avoid delay creep on certain configurations '
                    '(especially after the system is unfrozen).')

args = parser.parse_args()

assert not args.output_dir or os.path.isdir(args.output_dir), (
    'output_dir="%s" not found' % args.output_dir)

logger = util.createLogger('recorder')
if args.debug:
    logger.setLevel(logging.DEBUG)

conf = config.Config(logger)
hp = hotplug.HotPlug(logger)

running = True


def signal_handler(signal, frame):
    global running
    logger.info('Caught Ctrl-C')
    running = False


pysig.signal(pysig.SIGINT, signal_handler)


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
            # self.audio_interface.output_stream.write(buf.tostring())
            # dt = time.time() - t0
            # if dt < samples / settings.rate:
            #     time.sleep(samples / settings.rate - dt)
            self.t0 = time.time()
            if self.bufi >= len(data):
                self.stop()
        return buf

    def reset_audio_interface(self, audio_interface):
        self.audio_interface = audio_interface


class InputStreamer(object):

    def __init__(self, audio_interface, output_dir=None):
        self.audio_interface = audio_interface

        # will be initialized when .freeze(false) is called the first time
        self.wav = None
        self.t = 0
        self.t0 = time.time()
        self.data = np.zeros(settings.buf_size, dtype=np.float32)
        self.output_dir = output_dir

        self.player = Player(audio_interface)

    def freeze(self, frozen):
        if frozen:
            self.close()
        elif self.output_dir:
            now = int(time.time())
            self.wav_path = os.path.join(self.output_dir, '{}.wav'.format(now))
            self.wav = wave.open(self.wav_path, 'wb')
            self.wav.setnchannels(1)
            self.wav.setframerate(settings.rate)
            self.wav.setsampwidth(settings.sampwidth)

    @perf.measure('InputStreamer.read')
    def read(self, samples):
        if self.player.playing():
            data16 = self.player.get(samples)
            data = util.int16_to_float(data16)
        else:
            data = self.audio_interface.input_stream.read(
                samples, exception_on_overflow=False)
            data16 = np.frombuffer(data, settings.dtype_np)
            data = util.int16_to_float(data16)
            data = hp.effects.microphone_effect(data, None)
        self.t += float(len(data)) / settings.rate
        if self.wav_path:
            self.wav.writeframesraw(data16)
        return data

    def clear_buffers(self):
        while self.audio_interface.input_stream.get_read_available():
            n = self.audio_interface.input_stream.read(
                self.audio_interface.input_stream.get_read_available())
            logger.info('Clearing buffers : read n={} bytes.'.format(n))

    @perf.measure('InputStreamer.get')
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
def get_signals(feats):
    signals = hp.signals.runner(features=feats, t=time.time())
    signals['mfccs'] = feats.mfccs
    signals['logmel'] = feats.logmel
    del signals['features']
    return signals


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
monitor_address = (args.address, settings.monitor_port)
fadecandy_address = (args.address, settings.fadecandy_port)
dmx_address = (args.address, settings.dmx_port)

i = 0
i_o = 0

last_alive = 0
stats = dict(started=0, recorded=0)
if os.path.exists(ALIVE_PATH):
    dst = os.path.join(os.path.dirname(ALIVE_PATH), timestamp() + '.json')
    os.rename(ALIVE_PATH, dst)

logger.info('Start recording.')
ai0 = audio.AudioInterface(input=1, device_index=hp.effects.input_device)
ai1 = audio.AudioInterface(output=2, device_index=hp.effects.output_device_1)
ai2 = None
if hp.effects.output_device_2 is None or hp.effects.output_device_2 >= 0:
    ai2 = audio.AudioInterface(
        output=2, device_index=hp.effects.output_device_2)
input_streamer = InputStreamer(ai0, output_dir=args.output_dir)
last_reset_t = time.time()

started = False
think_t0 = None
frozen = None
while running:
    if frozen != conf['frozen']:
        frozen = conf['frozen']
        input_streamer.freeze(frozen)
        if not frozen and args.reset_secs > 0:
            last_reset_t = 0  # Force reset (if enabled) after unfreeze.
    if frozen:
        time.sleep(settings.hop_secs)
        continue

    if args.reset_secs and time.time() - last_reset_t > args.reset_secs:
        logger.info('Re-initializing input_streamer after freeze.')
        del ai0
        ai0 = audio.AudioInterface(
                input=1, device_index=hp.effects.input_device)
        input_streamer.reset_audio_interface(ai0)
        last_reset_t = time.time()
    t0 = time.time()
    feats = input_streamer.get()

    # intensity = ceps.max()
    i += 1
    # overdrive = bool(is_over(data).mean() > args.overdrive_threshold)
    # i_o += overdrive

    if args.alive_secs and (
            i - last_alive) * settings.hop_secs > args.alive_secs:
        stats['ts'] = timestamp()
        stats['i'] = i
        stats['i_o'] = i_o
        with open(ALIVE_PATH, 'w') as f:
            json.dump(stats, f)
        last_alive = i

    signals = get_signals(feats)

    bufs = hp.effects.effector(feats.wav[-settings.hop_size:], signals)
    ai1.output_stream.write(audio.tostereo(*bufs[:2]).tostring())
    if ai2:
        ai2.output_stream.write(audio.tostereo(*bufs[2:4]).tostring())

    if conf['logmel_src'].startswith('output'):
        channel = int(conf['logmel_src'][-1])
        signals['logmel'] = features.wav2features(
            hp.effects.effector.bufs[channel].buf).logmel

    lighter_message = {}
    # if overdrive:
    #     lighter_message['overdrive'] = True

    # if keeper.add(data, ceps, logmel) and args.output_dir:
    #     stats['recorded'] += 1
    #     msg = store(np.concatenate(keeper.bufs.data.as_list()),
    #                 keeper.stats())
    #     signals['msg'] = msg
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

    signals = util.pythonize(signals)
    signals = json.dumps(signals).encode('utf8')
    sock.sendto(signals, monitor_address)

    sock.sendto(signals, fadecandy_address)
    sock.sendto(signals, dmx_address)

logger.info('Stop recording.')
del input_streamer
del ai0
del ai1
if ai2:
    del ai2

print('\nPERF STATS:')
print(perf.stats())
