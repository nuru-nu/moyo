#include "CmdMessenger.h"

#define TRIG_PIN 9
#define ECHO_PIN 8

float max_dist = 60.0;     // Centimeters
long const pulse_time_max = (2 * (max_dist * 2)) / 0.0343;

/* Define available CmdMessenger commands */
enum {
  get_sonar,
  sonar_dist,
  error,
};

/* Initialize CmdMessenger -- this should match PyCmdMessenger instance */
const int BAUD_RATE = 9600;
CmdMessenger c = CmdMessenger(Serial,',',';','/');

/* Create callback functions to deal with incoming messages */

/* callback */
void on_get_sonar(void){
    float single_dist = read_sonar();
    c.sendBinCmd(sonar_dist, single_dist);
}

/* callback */
void on_unknown_command(void){
    c.sendCmd(error, "Command without callback.");
}

/* Attach callbacks for CmdMessenger commands */
void attach_callbacks(void) { 
  
    c.attach(get_sonar, on_get_sonar);
    c.attach(on_unknown_command);
}


void setup() {
  // sanity check delay - allows reprogramming if accidently blowing power w/leds
  delay(2000);

  // setup ultra sonic sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.begin(BAUD_RATE);
  attach_callbacks();  

}

void loop() {
  c.feedinSerialData();
  // long single_dist = read_sonar();

  // if(single_dist != 0.0) {

  //   if (single_dist <= max_dist){
  //     // presence
  //   }

  //   Serial.print(max_dist);
  //   Serial.print(", ");
  //   Serial.println(single_dist);
  // }
}

float read_sonar() {

  // Create a 10ms pulse. Switch the trigger pin to HIGH for 10 microseconds
  // Ensure the trigger pin is off, by setting it to LOW for 2 microseconds
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Measure the length of time it takes a pulse to an object and return back to the sensor.
  long duration = pulseIn(ECHO_PIN, HIGH, pulse_time_max);

  // Using the speed of sound you can calculate the distance from the duration of the flight of the pulse
  return (duration*.0343)/2.0;
}

