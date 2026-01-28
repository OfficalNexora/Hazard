/*
* MOD-EVAC-MS - Main Controller Firmware
* Platform: ESP32
* Features:
* - MPU6050 Accelerometer/Gyroscope
* - Rain Sensor (Analog)
* - Fire Sensor (Digital)
* - Serial Telemetry (JSON)
* - LED Status Indicators
*/

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// ==========================================
// PIN DEFINITIONS
// ==========================================
#define PIN_RAIN_ANALOG 34
#define PIN_FIRE_DIGITAL 35  // Digital Output from Flame Sensor
#define PIN_LED_SAFE 18      // Green
#define PIN_LED_WARN 19      // Orange
#define PIN_LED_DANGER 23    // Red
#define PIN_BUZZER 5

// ==========================================
// CONFIGURATION
// ==========================================
const long TELEMETRY_INTERVAL = 200; // ms
unsigned long lastTelemetryTime = 0;

// ==========================================
// OBJECTS
// ==========================================
Adafruit_MPU6050 mpu;

// ==========================================
// STATE
// ==========================================
struct SensorState {
  bool fire;
  int rain_level;
  float accel_x;
  float accel_y;
  float accel_z;
  float gyro_x;
  float gyro_y;
  float gyro_z;
};

SensorState currentSensors;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10); // Wait for serial console

  // Pin Modes
  pinMode(PIN_RAIN_ANALOG, INPUT);
  pinMode(PIN_FIRE_DIGITAL, INPUT);
  pinMode(PIN_LED_SAFE, OUTPUT);
  pinMode(PIN_LED_WARN, OUTPUT);
  pinMode(PIN_LED_DANGER, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  // Initialize LEDs (Test)
  digitalWrite(PIN_LED_SAFE, HIGH);
  delay(200);
  digitalWrite(PIN_LED_SAFE, LOW);

  // Initialize MPU6050
  if (!mpu.begin()) {
    Serial.println("{\"event\":\"error\",\"message\":\"MPU6050 validation failed\"}");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  Serial.println("{\"event\":\"boot\",\"status\":\"ready\"}");
}

void readSensors() {
  // 1. Read Fire Sensor (Logic: LOW usually means Fire Detected on standard modules, confirm hardware!)
  // Assuming standard IR Flame sensor: LOW = Fire detected, HIGH = No Fire
  // We invert it for boolean logic: Fire = true
  int fireVal = digitalRead(PIN_FIRE_DIGITAL);
  currentSensors.fire = (fireVal == LOW); 

  // 2. Read Rain Sensor
  currentSensors.rain_level = analogRead(PIN_RAIN_ANALOG);

  // 3. Read MPU6050
  sensors_event_t a, g, temp;
  if (mpu.getEvent(&a, &g, &temp)) {
    currentSensors.accel_x = a.acceleration.x;
    currentSensors.accel_y = a.acceleration.y;
    currentSensors.accel_z = a.acceleration.z;
    currentSensors.gyro_x = g.gyro.x;
    currentSensors.gyro_y = g.gyro.y;
    currentSensors.gyro_z = g.gyro.z;
  }
}

void sendTelemetry() {
  StaticJsonDocument<512> doc;
  
  doc["type"] = "telemetry";
  doc["fire"] = currentSensors.fire;
  doc["raining"] = currentSensors.rain_level; // Raw value, can map to % in backend
  
  JsonObject accel = doc.createNestedObject("accel");
  accel["x"] = currentSensors.accel_x;
  accel["y"] = currentSensors.accel_y;
  accel["z"] = currentSensors.accel_z;

  JsonObject gyro = doc.createNestedObject("earthquake"); // keeping legacy name for backend compat
  gyro["x"] = currentSensors.gyro_x;
  gyro["y"] = currentSensors.gyro_y;
  gyro["z"] = currentSensors.gyro_z;

  serializeJson(doc, Serial);
  Serial.println();
}

void handleCommand(String input) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, input);

  if (error) return;

  const char* cmd = doc["cmd"];
  
  if (strcmp(cmd, "set_alert") == 0) {
    int alertLevel = doc["alert"];
    // 0=Safe, 1-2=Warn, 3-4=Danger
    digitalWrite(PIN_LED_SAFE, alertLevel == 0 ? HIGH : LOW);
    digitalWrite(PIN_LED_WARN, (alertLevel >= 1 && alertLevel <= 2) ? HIGH : LOW);
    digitalWrite(PIN_LED_DANGER, alertLevel >= 3 ? HIGH : LOW);
    
    if (alertLevel >= 3) {
      digitalWrite(PIN_BUZZER, HIGH);
    } else {
      digitalWrite(PIN_BUZZER, LOW);
    }
    
    Serial.print("{\"event\":\"alert_set\",\"alert\":");
    Serial.print(alertLevel);
    Serial.println("}");
  }
  else if (strcmp(cmd, "ping") == 0) {
    Serial.print("{\"event\":\"pong\",\"uptime\":");
    Serial.print(millis());
    Serial.println("}");
  }
}

void loop() {
  // Non-blocking loop
  unsigned long currentMillis = millis();

  // 1. Read Serial Commands
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    handleCommand(input);
  }

  // 2. Read Sensors & Send Telemetry
  if (currentMillis - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    lastTelemetryTime = currentMillis;
    readSensors();
    sendTelemetry();
  }
}
