"""Streams animations & handles websockets.

This script opens reads signals and creates animations. The animations
can be streamed to fadecandy, and both signals and animations can be
streamed via websockets. Messages received on the signals websocket are
forwarded to the signalin UDP port.
"""

import argparse, asyncio, datetime, json, socket, sys, time, traceback

from autobahn.asyncio.websocket import WebSocketServerFactory
from autobahn.asyncio.websocket import WebSocketServerProtocol
from autobahn.websocket.protocol import WebSocketProtocol

import numpy as np
import opc

import hotplug, network, settings, state, util


parser = argparse.ArgumentParser(
    description='Streams animations & handles websockets')
parser.add_argument('--debug', type=bool, default=False,
                    help='Whether debug output should be generated.')

parser.add_argument('--fps', type=int, default=60,
                    help='Frames per second for animation streaming.')
parser.add_argument('--fadecandy', type=bool, default=False,
                    help='Whether to stream animations to fadecandy.')

args = parser.parse_args()

logger = util.createLogger('animator')
hp = hotplug.HotPlug(logger, modules=('animations',))
if args.debug:
    logger.setLevel(logging.DEBUG)
logger.info('starting animator')


def isOpen(protocol):
    return (
        protocol is not None and
        hasattr(protocol, 'state') and
        protocol.state ==  WebSocketProtocol.STATE_OPEN
    )


class GlobalState:
    """Global state shared between coros."""

    # latest animation WS client connection (others will be closed)
    animation_ws_proto = None
    # latest signals WS client connection (others will be closed)
    signals_ws_proto = None
    # socket for sending signalin UDP
    signalin_sock = None
    # latest signals received from UDP
    signals = None
    # whether system is in frozen state
    frozen = False


class StreamingStats:
    """Helper class to periodically show stats."""

    def __init__(self, hz=0.1, delay0=1.0):
        self.t0 = time.time() - 1 / hz + delay0
        self.total = {}
        self.totaltotal = {}
        self.n = {}
        self.hz = hz

    def dump(self):
        """Dumps stats to logger.info()."""
        dt = time.time() - self.t0
        for name in sorted(self.total):
            logger.info('stats[%s] : %.1f fps %.1f kps (sum %.1fM)',
                        name, self.n[name]/dt, self.total[name]/dt/1e3,
                        self.totaltotal[name]/1e6)

    def __call__(self, name, s):
        """"Adds `s` to stats and calls dump() every 1/hz seconds."""
        if name not in self.n:
            self.n[name] = self.total[name] = self.totaltotal[name] = 0
        self.n[name] += 1
        if s is not None:
            self.total[name] += len(s)
            self.totaltotal[name] += len(s)
        t = time.time()
        dt = t - self.t0
        if dt * self.hz > 1:
            self.dump()
            self.t0 = t
            self.n[name] = self.total[name] = 0


class SignalsUdpProtocol(asyncio.DatagramProtocol):
    """Stores signals in `global_state.signals` and forwards to ws."""

    def __init__(self, stats, global_state):
        super().__init__()
        self.stats = stats
        self.global_state = global_state

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        logger.info('connection_made peer=%s', peername or '?')
        self.transport = transport

    def datagram_received(self, data, addr):
        global signals
        self.stats('signals_udp', data)
        signals = json.loads(data.decode('utf8'))
        signals['state'] = state.State(signals['state'])
        self.global_state.signals = signals
        if isOpen(self.global_state.signals_ws_proto):
            self.global_state.signals_ws_proto.sendMessage(
                data, isBinary=False)


class WsServerProtocol(WebSocketServerProtocol):
    """WebSocketServerProtocol that logs onConnect & onMessage."""

    which = None

    def __init__(self, global_state):
        super().__init__()
        self.global_state = global_state

    def onConnect(self, request):
        logger.info('onConnect[%s] request.peer=%s', self.which, request.peer)

    def onMessage(self, payload, isBinary):
        logger.info('onMessage[%s] : %s %s', self.which, payload, isBinary)


class AnimationWsProtocol(WsServerProtocol):

    which = 'animation'


class SignalsWsProtocol(WsServerProtocol):

    which = 'signals'

    def onMessage(self, payload, isBinary):
        super().onMessage(payload, isBinary)
        self.global_state.signalin_sock.sendto(
            payload, ('localhost', settings.signalin_port))


class SingleConnectionWsFactory(WebSocketServerFactory):
    """Forwards `global_state` and keeps single `attr` connection."""

    def __init__(self, global_state, attr):
        super().__init__()
        assert hasattr(global_state, attr)
        self.global_state = global_state
        self.attr = attr

    def __call__(self):
        if getattr(self.global_state, self.attr) is not None:
            logger.info('SingleConnectionWsFactory: sendClose')
            getattr(self.global_state, self.attr).sendClose(
                code=3000, reason='new connection')
        proto = self.protocol(self.global_state)
        proto.factory = self
        setattr(self.global_state, self.attr,  proto)
        return proto


class Animator:
    """Transforms `signals` to pixels."""

    def __call__(self, signals):
        return hp.animations.pixels(**signals)['value']

    # def __init__(self):
    #     arm_channels = set(
    #         arm_config.channel for arm_config in settings.arm_configs)
    #     self.all_arm_pixels = {
    #         channel: (
    #             # TODO dirty hack !
    #             np.zeros([10 * 64, 3]) if channel == 3
    #             else np.zeros([8 * 64, 3])
    #         )
    #         for channel in arm_channels
    #     }

    # def __call__(self, signals):
    #     sphere_pixels = hp.animations.sphere(**signals)['value']
    #     for arm_config, arm in zip(settings.arm_configs, hp.animations.arms):
    #         arm_pixels = arm(**signals)['value']
    #         i = 0
    #         for offsets in arm_config.offsets:
    #             for offset in offsets:
    #                 self.all_arm_pixels[
    #                     arm_config.channel][offset: offset + 64, :] = (
    #                         arm_pixels[i * 64: (i + 1) * 64])
    #                 i += 1
    #         # TODO dirty hack!
    #         self.all_arm_pixels[4][0: 2 * 64] = self.all_arm_pixels[3][8 * 64:]
    #     return {
    #         channel: pixels
    #         for channel, pixels in list(self.all_arm_pixels.items()) + [
    #             (0, sphere_pixels[:512]),
    #             (1, sphere_pixels[512:]),
    #         ]
    #     }
    #

def pad_fadecandy(values):
    """Adds 4 zero RGBs after every 60 values."""
    zeros = np.zeros((4, 3), 'uint8')
    return np.concatenate([
        np.concatenate([
            values[i0: i0 + 60],
            zeros
        ])
        for i0 in range(0, values.shape[0], 60)
    ])

async def render_loop(animator, client, fps, stats, global_state):
    t0 = time.time()
    try:
        while True:

            dt = time.time() - t0
            await asyncio.sleep(max(0, 1 / fps - dt))
            t0 = time.time()

            if not global_state.signals or global_state.frozen:
                continue

            pixels = animator(global_state.signals)
            data = pixels
            data = np.clip((255 * data).astype('uint8'), 0, 255)
            stats('animation', data)

            try:
                if client:
                    fc_data = pad_fadecandy(data)
                    ok = True
                    for channel, i0 in enumerate(range(0, fc_data.shape[0], 512)):
                        ok &= client.put_pixels(fc_data[i0: i0 + 512], channel + 1)
                    if ok:
                        stats('fc_animation', fc_data)
            except e:
                print('COULD NOT FC', e)

            if isOpen(global_state.animation_ws_proto):
                stats('ws_animation', data)
                global_state.animation_ws_proto.sendMessage(
                    data.tostring(), isBinary=True)

    except Exception as e:
        logger.fatal('render_loop FAILED : %s', e)
        print(traceback.format_exc())
        sys.exit(-1)


def main():
    client = None
    if args.fadecandy:
        client = opc.Client('localhost:7890')
        assert client.can_connect()
        client.set_interpolation(False)
    stats = StreamingStats()
    animator = Animator()
    global_state = GlobalState()
    global_state.signalin_sock = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM)

    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    animation_factory = SingleConnectionWsFactory(
        global_state, 'animation_ws_proto')
    animation_factory.protocol = AnimationWsProtocol
    animation_server = loop.run_until_complete(
        loop.create_server(
            animation_factory, settings.ws_address, settings.ws_animation_port))

    signals_factory = SingleConnectionWsFactory(
        global_state, 'signals_ws_proto')
    signals_factory.protocol = SignalsWsProtocol
    signals_server = loop.run_until_complete(
        loop.create_server(
            signals_factory, settings.ws_address, settings.ws_signals_port))

    transport = loop.create_datagram_endpoint(
        lambda: SignalsUdpProtocol(stats, global_state),
        local_addr=('127.0.0.1', settings.fadecandy_port))
    loop.run_until_complete(transport)

    render_task = asyncio.ensure_future(render_loop(
        animator, client, args.fps, stats, global_state))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        render_task.cancel()  # await?
        signals_server.close()
        animation_server.close()
        loop.close()


if __name__ == '__main__':
    main()

