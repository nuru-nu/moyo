
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

parser.add_argument('--monitor_freq', type=float, default=10.,
                    help='Monitor update frequency.')
args = parser.parse_args()

logger = util.createLogger('monitor')
if args.debug:
    logger.setLevel(logging.DEBUG)
logger.info('starting monitor')

conf = config.Config(logger)


class Stats:
    """Keeps min, max, fps and reports periodically."""

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
        """Returns string representation, also resets `self.t0`."""
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
        self.rows = []
        self.i = 0
        self.ignore = ignore
        self.palette = [
            ''.join([c, s])
            for s in ('-', '--', ':', '-.')
            for c in 'krgbm'
        ]
        self.lines = dict(ax1={}, ax2={})
        self.zeros = np.zeros(steps)
        self.clear()

    def clear(self):
        self.data = {}
        self.cols = {}
        self.vars = {}
        self.mtimes = {}

    def create(self, key):
        if self.i % 6 == 0:
            row = ttk.Frame(self.controls)
            row.pack(side=tk.TOP)
            self.rows.append(row)
        self.i += 1
        ax = 'ax2' if key[0] == '_' else 'ax1'
        self.data[key] = self.zeros.copy()
        self.cols[key] = self.palette[len(self.data) % len(self.palette)]
        self.lines[ax][key], = self.axs['ax1'].plot(
            self.data[key], self.cols[key])
        text = '{} ({})  '.format(key, self.cols[key])
        self.vars[key] = var = tk.IntVar()
        var.set(1 if key in ('loud', 'pitch') else 0)
        ttk.Checkbutton(self.rows[-1], text=text, variable=var).pack(
            side=tk.LEFT)

    def update(self, data):
        t = time.time()
        for k, v in data.items():
            if k in self.ignore:
                continue
            if not isinstance(v, float):
                continue
            self.mtimes[k] = t
            if k not in self.data:
                self.create(k)
            self.data[k] = np.roll(self.data[k], shift=-1)
            self.data[k][-1] = v

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

        self.signalin_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.signalin_address = (settings.address, settings.signalin_port)

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
        self.logmel_src = tk.StringVar()
        self.logmel_src.set(conf['logmel_src'])
        for logmel_src in ['input', 'output0', 'output1']:
            ttk.Radiobutton(
                top_buttons, value=logmel_src, text=logmel_src,
                command=self.update_logmel,
                variable=self.logmel_src).pack(side=tk.LEFT)
        self.freeze_button = ttk.Button(
            top_buttons, text='(un)freeze', command=self.freeze)
        self.freeze_button.pack(side=tk.LEFT)
        ttk.Button(top_buttons, text='store', command=self.store).pack(
            side=tk.LEFT)
        ttk.Button(top_buttons, text='quit', command=self.shutdown).pack(
            side=tk.LEFT)
        top_buttons.pack()

        state_buttons = ttk.Frame(top)
        self.state = tk.StringVar()
        self.state.set('...')
        ttk.Label(state_buttons, textvariable=self.state).pack(side=tk.LEFT)
        for i, state in enumerate(('std', 'ooo', 'flash', 'drone')):
            text = '<{}> {}'.format(i + 1, state)
            command = functools.partial(self.send, dict(state=state))
            button = ttk.Button(state_buttons, text=text, command=command)
            self.root.bind(str(i + 1), lambda _: command)
            button.pack(side=tk.LEFT)
        state_buttons.pack()

        recording_frame = ttk.Frame(top)
        self.recording_entry = tk.StringVar()
        entry = ttk.Entry(recording_frame, textvariable=self.recording_entry)
        entry.pack(side=tk.LEFT)
        ttk.Button(recording_frame, text='record', command=self.recordit).pack(
            side=tk.LEFT)
        recording_frame.pack()
        entry.bind('<Return>', self.recordit)
        top.bind('<Return>', self.recordit)

        self.play = tk.StringVar()
        values = sorted(list(settings.get_recordings().keys()))
        ttk.Combobox(recording_frame, values=values,
                     textvariable=self.play).pack(side=tk.LEFT)
        ttk.Button(recording_frame, text='play',
                   command=lambda: self.send(dict(play=self.play.get()))
                   ).pack(side=tk.LEFT)

        top_labels = ttk.Frame(top)
        ttk.Label(top_labels, text=settings.to_string()).pack(side=tk.LEFT)
        self.fpsvar = tk.StringVar()
        ttk.Label(top_labels, textvar=self.fpsvar).pack(side=tk.LEFT)
        top_labels.pack()
        top.pack()

        self.fig = Figure(figsize=(8, 5), dpi=100)
        ax1 = self.fig.add_subplot(211)
        self.img = ax1.matshow(self.logmel.T, cmap='jet')
        ax1.set_xticks([])
        ax1.set_yticklabels([
            '{:,}'.format(int(f * settings.f2hz))
            for f in ax1.get_yticks()
        ])
        ax2 = self.ax2 = self.fig.add_subplot(212)
        ax2.set_ylim([0, 1.1])
        ax3 = ax2.twinx()
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

    def recordit(self, *_):
        now = int(time.time())
        name = self.recording_entry.get()
        if name:
            with open(settings.recorder2_index, 'a') as f:
                f.write('{},{}\n'.format(now, name))
            logger.info('Recorded {}'.format(name))
            if name.endswith('_stop'):
                self.recording_entry.set('')
            else:
                self.recording_entry.set('{}_stop'.format(name))

    def update_logmel(self):
        conf['logmel_src'] = self.logmel_src.get()

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

    def send(self, d):
        logger.info('sending {}'.format(d))
        msg = json.dumps(d).encode('utf8')
        self.signalin_sock.sendto(msg, self.signalin_address)

    def anim(self, *args):
        while self.recv():
            self.stats.inc('recv')
        self.updateui()

    def updateui(self):
        if self.stats.ready():
            self.ax2.set_title(self.stats.get())
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
            self.state.set(data.get('state', '?'))
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
