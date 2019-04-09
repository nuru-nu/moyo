
import argparse, functools, io, json, logging, socket
import time

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import W, E, N, S
from tkinter import ttk
from matplotlib import animation
import numpy as np

import settings, util


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


class Monitor:

    def __init__(self):
        self.t0 = time.time()
        self.stats = Stats()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0)
        self.sock.bind((args.listen_address, args.port))

        self.recorder_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recorder_address = (args.address, args.recorder_port)

        self.steps = 200
        self.data = np.zeros((self.steps, settings.num_mel_bins))
        self.loud = np.zeros(self.steps)
        self.pitch = np.zeros(self.steps)
        self.data[0, 0] = -6
        self.data[0, 1] = 5

        self.initui()

    def initui(self):
        self.root = tk.Tk()
        self.root.wm_title('rizhoom monitor')
        self.root.protocol('WM_DELETE_WINDOW', self.shutdown)
        self.root.resizable(False, False)

        top = ttk.Frame(self.root)
        ttk.Label(top, text=settings.to_string()).pack()
        self.fpsvar = tk.StringVar()
        ttk.Label(top, textvar=self.fpsvar).pack()
        top.grid(column=0, row=0, sticky=(E, W))

        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax1 = self.fig.add_subplot(211)
        self.ax1.set_xticks([])
        self.ax1.set_yticks([])
        self.img = self.ax1.matshow(self.data.T, cmap='jet')
        self.ax2 = self.fig.add_subplot(212)
        self.ax2.set_ylim([0, .3])
        self.ax2.set_ylabel('loud (blue)')
        self.line_loud, = self.ax2.plot(self.loud, 'b')
        self.ax3 = self.ax2.twinx()
        self.ax3.set_ylim([0, 800])
        self.ax3.set_ylabel('pitch (red)')
        self.line_pitch, = self.ax3.plot(self.pitch, 'r')

        self.frame = ttk.Frame(self.root)
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(
            column=0, row=0, sticky=(N, W, E, S))

        self.frame.grid(column=0, row=1, columnspan=2, sticky=(N, W, E, S))
        self.ani = animation.FuncAnimation(
            self.fig, self.anim, interval=1000 / args.monitor_freq, blit=False)

        buttons = ttk.Frame(self.root)
        for name in sorted(settings.recordings):
            ttk.Button(buttons, text=name,
                       command=functools.partial(self.play, name)
                       ).pack(side=tk.LEFT)
        buttons.grid(column=0, row=2, sticky=E)

    def play(self, name):
        logger.info('Playing {}'.format(name))
        msg = json.dumps({
            'play': name,
        }).encode('utf8')
        self.recorder_sock.sendto(msg, self.recorder_address)

    def anim(self, *args):
        self.stats.inc('anim')
        while self.recv():
            self.stats.inc('recv')
            pass
        self.img.set_data(self.data.T)
        self.line_loud.set_ydata(self.loud)
        self.line_pitch.set_ydata(self.pitch)
        if self.stats.ready():
            self.fpsvar.set(self.stats.get())

    def shutdown(self):
        logger.info('shutting down...')
        del self.ani
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
        self.data = np.roll(self.data, shift=-1, axis=0)
        self.stats.minmax('logmel', data['logmel'])
        self.data[-1, :] = data['logmel']
        self.loud = np.roll(self.loud, shift=-1, axis=0)
        self.loud[-1] = data.get('loud', 0)
        self.stats.minmax('loud', self.loud[-1])
        self.pitch = np.roll(self.pitch, shift=-1, axis=0)
        self.pitch[-1] = data.get('pitch', 0)
        self.stats.minmax('pitch', self.pitch[-1])
        return True


monitor = Monitor()
monitor.root.mainloop()
