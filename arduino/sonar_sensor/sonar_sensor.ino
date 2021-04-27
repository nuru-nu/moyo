#define TRIG_PIN 9
#define ECHO_PIN 8

float max_dist = 60.0;     // Centimeters
long const pulse_time_max = (2 * (max_dist * 2)) / 0.0343;

void setup()
{
  // sanity check delay - allows reprogramming if accidently blowing power w/leds
  delay(2000);
  
  Serial.begin(57600);

  // setup ultra sonic sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop()
{
  Serial.println("S:" + String(read_sonar()));
}

int read_sonar() {
  // Create a 10ms pulse. Switch the trigger pin to HIGH for 10 microseconds
  // Ensure the trigger pin is off, by setting it to LOW for 2 microseconds
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Measure the length of time it takes a pulse to an object and return back to the sensor.
  long duration_us = pulseIn(ECHO_PIN, HIGH, pulse_time_max);

  // Using the speed of sound you can calculate the distance from the duration of the flight of the pulse
  float distance_cm = (duration_us / 1e6 * 100 * 343) / 2.0;
  return int(distance_cm);
}