import time

import serial
import PyCmdMessenger

import network, settings, util


logger = util.createLogger('arduino_signals')

# List of commands and their associated argument formats. These must be in the
# same order as in the sketch.
commands = [["get_sonar",""],
			["sonar_dist","f"],
			["error","s"]]

connected = False
for arduino_port in settings.arduino_ports:
	try:
		arduino = PyCmdMessenger.ArduinoBoard(
			arduino_port, baud_rate=9600)
		break
	except serial.serialutil.SerialException:
		logger.info('Could NOT connect to {}...'.format(arduino_port))
assert arduino is not None, 'Could not connect to any Arduino port!!'
arduino = PyCmdMessenger.CmdMessenger(arduino, commands)

logger.info("Connected to Arduino on port " + arduino_port)

signalin_sender = network.SignalinSender(logger)

def read_sonar(): 
    arduino.send("get_sonar")
    msg = arduino.receive()
    if msg is None or (len(msg) < 1):
    	return -1
    else:
    	return msg[1][0]

while True:
	signalin_sender.send(dict(sonar=read_sonar()))
	time.sleep(1 / settings.sonar_hz)
