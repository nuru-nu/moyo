#include <CapacitiveSensor.h>

#define SENSORS 3
#define OFFSET 2  // Pins 0 & 1 are used for rx/tx comm.
CapacitiveSensor *sensors[SENSORS];

void setup()
{
    Serial.begin(57600);

    for (uint8_t i = 0; i < SENSORS; ++i)
    {
        // Circuit diagram:
        //
        // Arduino.PIN(2*i)-------+
        //                        |
        //                   (1M or 10M)
        //                        |
        // Arduino.PIN(2*i+1)-----+-------------(sensing mesh)
        //
        sensors[i] = new CapacitiveSensor(OFFSET + i * 2, OFFSET + i * 2 + 1);
        // sensors[i] = new CapacitiveSensor(8, 7);
    }

    // Trigger re-calibration manually.
    // capsens.reset_CS_AutoCal();

    // capsens.set_CS_AutocaL_Millis(5000);
    // Default values from library:
    // capsens.set_CS_AutocaL_Millis(20000);
    // capsens.set_CS_Timeout_Millis((2000 * (float)310 * (float)F_CPU) / 16000000);
}

void loop()
{
    // Serial.println(capsens[0]->capacitiveSensor(30));

    // This will re-calibrate every AutocaL_Millis "unless touched" - based on
    // a crude thresholded heuristic...
    for (uint8_t i = 0; i < SENSORS; ++i)
    {
        Serial.print(sensors[i]->capacitiveSensor(15));
        Serial.print(i == SENSORS - 1 ? '\n' : ',');
    }

    // This one is not calibrated and does not autocalibrate.
    // -> Less useful because it has a large baseline value.
    // Serial.println(capsens.capacitiveSensorRaw(30));
}
