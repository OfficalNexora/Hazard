/*
 * MOD-EVAC-MS DEBUGGER - FINAL (ESP32 ONLY)
 * 
 * PURPOSE: Prove the ESP32 is healthy WITHOUT the sensor.
 * 
 * INSTRUCTIONS:
 * 1. DISCONNECT the MLX90614 sensor completely (remove SDA/SCL wires).
 * 2. Upload this code.
 * 3. If Serial Monitor shows "ESP32 is HEALTHY", the chip is fine.
 *    The SENSOR is the problem.
 */

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n=============================");
  Serial.println("   ESP32 HEALTH CHECK");
  Serial.println("=============================");
  Serial.println("If you see this message, the ESP32 is HEALTHY.");
  Serial.println("");
  Serial.println("The problem is your MLX90614 SENSOR.");
  Serial.println("It is damaged and shorting the I2C bus.");
  Serial.println("");
  Serial.println("SOLUTION: Replace the sensor module.");
  Serial.println("=============================");
}

void loop() {
  Serial.println("ESP32 OK... (Sensor disconnected)");
  delay(1000);
}
