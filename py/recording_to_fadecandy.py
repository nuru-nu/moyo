import time
import numpy as np
import colorsys
import socket
import json

import opc
import settings

numLEDs = 60
# client = opc.Client('localhost:7890')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.settimeout(None)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((settings.address, settings.monitor_port))

while True:
    data, address = sock.recvfrom(4096)
    data = json.loads(data.decode("utf8"))
    brightness = np.clip((data["loud"] - 0) * 850, 0, 255)
    hue = np.clip(data["pitch"] * 0.6, 0, 360)

    colors = [([v * 255 for v in colorsys.hsv_to_rgb(
        hue / 360.0, 1.0, brightness / 255.0)])] * numLEDs
    # client.put_pixels(colors)
