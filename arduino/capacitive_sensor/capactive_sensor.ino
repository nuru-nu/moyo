#include <CapacitiveSensor.h>

CapacitiveSensor capsens = CapacitiveSensor(8, 7);  // 8 -> 1M -> 7 (sensor)

void setup() {
    Serial.begin(9600);

    // Trigger re-calibration manually.
    // capsens.reset_CS_AutoCal();

    // capsens.set_CS_AutocaL_Millis(5000);
    // Default values from library:
    // capsens.set_CS_AutocaL_Millis(20000);
    // capsens.set_CS_Timeout_Millis((2000 * (float)310 * (float)F_CPU) / 16000000);
}

void loop() {
    // This will re-calibrate every AutocaL_Millis "unless touched" - based on
    // a crude thresholded heuristic...
    Serial.println(capsens.capacitiveSensor(30));

    // This one is not calibrated and does not autocalibrate.
    // -> Less useful because it has a large baseline value.
    // Serial.println(capsens.capacitiveSensorRaw(30));
}
