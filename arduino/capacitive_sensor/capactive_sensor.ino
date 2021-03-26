#include <CapacitiveSensor.h>

CapacitiveSensor capsens = CapacitiveSensor(8, 7);  // 8 -> 1M -> 7 (sensor)

void setup() {
    Serial.begin(9600);
}

void loop() {
    Serial.println(capsens.capacitiveSensor(30));
}
