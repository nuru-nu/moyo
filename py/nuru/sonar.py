import time

import serial
import PyCmdMessenger

from smanmi import network, util
from . import settings


logger = util.createLogger('arduino_signals')

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
        return -1
    arduino.send("get_sonar")
    msg = arduino.receive()
    if msg is None or (len(msg) < 1):
        return -1
    else:
        return msg[1][0]


sock = network.create_udp_socket(
    settings.sonar_cmd_port, settings.address)
override = None
while True:
    data = network.get_json(sock, None)
    if data:
        override = data.get('sonar')
        logger.info('override=%r', override)
    network.send(settings.integrator_sig_port, dict(
        sonar=override if override is not None else read_sonar(),
    ))
    time.sleep(1 / settings.sonar_hz)
