"""Reads sonar signal from Arduino as `sonar` [m] (or 0.0 if no signal)."""
import time

import serial
import PyCmdMessenger

from smanmi import network, util
from . import settings


logger = util.createLogger('sonar')

# List of commands and their associated argument formats. These must be in the
# same order as in the sketch.
commands = [["get_sonar", ""],
            ["sonar_dist", "f"],
            ["error", "s"]]

connected = False
arduino = None
for arduino_port in settings.arduino_ports:
    try:
        arduino = PyCmdMessenger.ArduinoBoard(
            arduino_port, baud_rate=9600)
        break
    except serial.serialutil.SerialException:
        logger.info('Could NOT connect to {}...'.format(arduino_port))

if arduino:
    logger.info("Connected to Arduino on port " + arduino_port)
    arduino = PyCmdMessenger.CmdMessenger(arduino, commands)
else:
    logger.error('Could not connect to any Arduino!')


def read_sonar():
    if arduino is None:
        return 0.
    arduino.send("get_sonar")
    msg = arduino.receive()
    if msg is None or (len(msg) < 1):
        return 0.
    else:
        # Sonar sensor returns cm.
        return max(0, min(1, msg[1][0] / 100.))


sock = network.create_udp_socket(settings.sonar_cmd_port, '127.0.0.1')
while True:
    data = network.get_json(sock, None)
    if data and 'sonar' in data:
        logger.info('received sonar=%s - DOING NOTHING', data['sonar'])
    sonar = read_sonar()
    network.send(settings.integrator_sig_port, dict(sonar_sensor=sonar))
    time.sleep(1 / settings.sonar_hz)
