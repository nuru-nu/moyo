
import argparse, functools, io, json, logging, os, pickle, socket
import time

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
from matplotlib import animation
import numpy as np

import config, settings, util


matplotlib.use("TkAgg")

parser = argparse.ArgumentParser(
    description='Records audio and transforms the signal.')
parser.add_argument('--debug', type=bool, default=False,
                    help='Whether debug output should be generated.')

parser.add_argument('--listen_address', type=str, default=settings.address,
                    help='Which address to listen on.')
parser.add_argument('--port', type=int, default=settings.monitor_port,
                    help='Which port to listen on.')
parser.add_argument('--recorder_port', type=int,
                    default=settings.recorder_port,
                    help='Which port "recorder" is listening on.')
parser.add_argument('--address', type=str, default=settings.address,
                    help='Which address to send to.')

parser.add_argument('--monitor_freq', type=float, default=10.,
                    help='Monitor update frequency.')
args = parser.parse_args()

logger = util.createLogger('monitor')
if args.debug:
    logger.setLevel(logging.DEBUG)
logger.info('starting monitor')

conf = config.Config(logger)


class Stats:
    def __init__(self, freq=1):
        self.t0 = time.time()
        self.freq = freq
        self.reset()

    def reset(self):
        self.counts = {}
        self.mins = {}
        self.maxs = {}

    def minmax(self, name, x):
        try:
            [self.minmax(name, _) for _ in x]
            return
        except TypeError:
            pass
        self.mins[name] = min(x, self.mins.get(name, x))
        self.maxs[name] = max(x, self.maxs.get(name, x))

    def inc(self, name):
        self.counts[name] = 1 + self.counts.get(name, 0)

    def ready(self):
        return (time.time() - self.t0) > 1 / self.freq

    def get(self):
        dt = time.time() - self.t0
        self.t0 += dt
        counts = self.counts
        mins, maxs = self.mins, self.maxs
        self.reset()
        return ' '.join([
            '{}={:.1f}fps'.format(name, counts[name] / dt)
            for name in sorted(counts)
        ] + [
            '{}={:.1f}..{:.1f}'.format(
                name, mins[name], maxs[name])
            for name in sorted(mins)
        ])


class Graphs:
    """Updates two axes with incoming data."""

    def __init__(self, steps, controls, ax1, ax2, ignore=('logmel', 'mfccs')):
        """Using `ax1` for values 0..1 and `ax2` for values >1."""
        self.axs = dict(ax1=ax1, ax2=ax2)
        self.controls = controls
        self.ignore = ignore
        self.palette = 'krgbm'
        self.lines = dict(ax1={}, ax2={})
        self.data = {}
        self.cols = {}
        self.vars = {}
        self.mtimes = {}
        self.zeros = np.zeros(steps)

    def create(self, key):
        self.data[key] = self.zeros.copy()
        self.cols[key] = self.palette[len(self.data) % len(self.palette)]
        self.lines['ax1'][key], = self.axs['ax1'].plot(
            self.data[key], self.cols[key])
        text = '{} ({})  '.format(key, self.cols[key])
        self.vars[key] = var = tk.IntVar()
        var.set(1 if key in ('loud', 'pitch') else 0)
        ttk.Checkbutton(self.controls, text=text, variable=var).pack(
            side=tk.LEFT)

    def ax1ax2(self, key):
        self.lines['ax1'][key].set_ydata(self.zeros)
        del self.lines['ax1'][key]
        self.lines['ax2'][key], = self.axs['ax2'].plot(
            self.data[key], self.cols[key])
        self.updateui()

    def update(self, data):
        t = time.time()
        for k, v in data.items():
            if k in self.ignore:
                continue
            self.mtimes[k] = t
            if k not in self.data:
                self.create(k)
            self.data[k] = np.roll(self.data[k], shift=-1)
            self.data[k][-1] = v

            # move to 'ax2' if values > 1.0 are observed.
            if self.data[k].max() > 1.0 and k in self.lines['ax1']:
                self.ax1ax2(k)

    def updateui(self):
        for name, data in self.data.items():
            line = None
            for lines in self.lines.values():
                if name in lines:
                    line = lines[name]
                    break
            if self.vars[name].get():
                line.set_ydata(data)
            else:
                line.set_ydata(self.zeros)


class Monitor:

    def __init__(self):
        self.t0 = time.time()
        self.stats = Stats()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((args.listen_address, args.port))

        self.recorder_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recorder_address = (args.address, args.recorder_port)

        self.steps = 200
        self.logmel = np.zeros((self.steps, settings.num_mel_bins))
        self.logmel[0, 0] = -6
        self.logmel[0, 1] = 5

        self.initui()
        self.update_freeze()

    def initui(self):
        self.root = tk.Tk()
        self.root.wm_title('rizhoom monitor')
        self.root.resizable(False, False)
        # "close" button hangs ...
        # ... doesn't really work
        self.root.protocol('WM_DELETE_WINDOW', self.shutdown)
        # ... also disables ttk.Entry selection
        # self.root.overrideredirect(True)

        self.style = ttk.Style(self.root)
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', background='white')

        top = ttk.Frame(self.root)
        top_buttons = ttk.Frame(top)
        self.freeze_button = ttk.Button(
            top_buttons, text='(un)freeze', command=self.freeze)
        self.freeze_button.pack(side=tk.LEFT)
        ttk.Button(top_buttons, text='store', command=self.store).pack(
            side=tk.LEFT)
        ttk.Button(top_buttons, text='quit', command=self.shutdown).pack(
            side=tk.LEFT)
        top_buttons.pack()
        top_labels = ttk.Frame(top)
        ttk.Label(top_labels, text=settings.to_string()).pack(side=tk.LEFT)
        self.fpsvar = tk.StringVar()
        ttk.Label(top_labels, textvar=self.fpsvar).pack(side=tk.LEFT)
        top_labels.pack()
        top.pack()

        self.axs = {}
        self.fig = Figure(figsize=(8, 5), dpi=100)
        ax1 = self.fig.add_subplot(211)
        ax1.set_xticks([])
        ax1.set_yticks([])
        self.img = ax1.matshow(self.logmel.T, cmap='jet')
        self.axs['ax2'] = ax2 = self.fig.add_subplot(212)
        ax2.set_ylim([0, 1.1])
        self.axs['ax3'] = ax3 = ax2.twinx()
        ax3.set_ylim([0, 800])

        self.frame = ttk.Frame(self.root)
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack()

        self.frame.pack()
        self.ani = animation.FuncAnimation(
            self.fig, self.anim, interval=1000 / args.monitor_freq, blit=False)

        controls = ttk.Frame(self.root)
        controls_row1 = ttk.Frame(controls)
        self.graphs = Graphs(
            steps=self.steps, controls=controls_row1, ax1=ax2, ax2=ax3)
        controls_row1.pack()
        controls_row2 = ttk.Frame(controls)
        self.confvars = {}
        # for name in ('loud_scale', 'pitcher_tolerance'):
        for name in ():
            self.confvars[name] = var = tk.StringVar()
            var.set(conf[name])
            ttk.Label(controls_row2, text=' {}='.format(name)).pack(
                side=tk.LEFT)
            ttk.Entry(controls_row2, textvariable=var, width=4).pack(
                side=tk.LEFT)
        controls_row2.pack()
        controls.pack()

        button_rows = ttk.Frame(self.root)
        first_letters = None
        for name in sorted(settings.get_recordings()):
            if first_letters != name[:3]:
                first_letters = name[:3]
                button_row = ttk.Frame(button_rows)
            command = functools.partial(self.play, name)
            ttk.Button(button_row, text=name, command=command).pack(
                side=tk.LEFT)
            button_row.pack(side=tk.TOP)
        button_rows.pack()

    def freeze(self):
        conf['frozen'] = 1 - conf['frozen']
        self.update_freeze()

    def update_freeze(self):
        if conf['frozen']:
            self.ani.event_source.stop()
            self.freeze_button.configure(text='unfreeze')
        else:
            self.ani.event_source.start()
            self.freeze_button.configure(text='freeze')

    def store(self):
        i = 0
        while True:
            path = 'logmel{:03d}.pickle'.format(i)
            if not os.path.exists(path):
                break
            i += 1
        with open(path, 'wb') as f:
            pickle.dump(self.logmel, f)
        logger.info('stored logmel to "{}"'.format(path))

    def play(self, name):
        logger.info('Playing {}'.format(name))
        msg = json.dumps({
            'play': name,
        }).encode('utf8')
        self.recorder_sock.sendto(msg, self.recorder_address)

    def anim(self, *args):
        while self.recv():
            self.stats.inc('recv')
        self.updateui()

    def updateui(self):
        if self.stats.ready():
            self.axs['ax2'].set_title(self.stats.get())
        for name, var in self.confvars.items():
            try:
                value = float(var.get())
            except ValueError:
                value = 0
                var.set(value)
            # don't bother to read from conf
            conf[name] = value

        self.stats.inc('anim')
        self.img.set_data(self.logmel.T)
        self.graphs.updateui()

    def shutdown(self):
        logger.info('shutting down...')
        # del self.ani
        self.ani.event_source.stop()
        self.root.destroy()

    def recv(self):
        try:
            data, address = self.sock.recvfrom(4096)
        except io.BlockingIOError:
            return False
        try:
            data = json.loads(data.decode('utf8'))
        except json.JSONDecodeError as e:
            logger.warning('Could not decode {!r} : {}'.format(data, e))
            return False
        self.logmel = np.roll(self.logmel, shift=-1, axis=0)
        self.stats.minmax('logmel', data['logmel'])
        self.logmel[-1, :] = data['logmel']

        self.graphs.update(data)
        return True


monitor = Monitor()
monitor.root.mainloop()
