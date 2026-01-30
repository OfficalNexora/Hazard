/*
* MOD-EVAC-MS - Main Controller Firmware
* Platform: ESP32
* Features:
* - MPU6050 Accelerometer/Gyroscope
* - Rain Sensor (Analog)
* - Fire Sensor (Digital)
* - Serial Telemetry (JSON)
* - WS2812B LED Strip (Evacuation Guidance)
*/

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_NeoPixel.h>

// ==========================================
// PIN DEFINITIONS (Synced with accelometer.ino)
// ==========================================
// Primary I2C (Seismic - MPU6050)
#define I2C_SDA 21
#define I2C_SCL 22

// Secondary I2C (Fire - MLX90614)
#define FIRE_SDA 25
#define FIRE_SCL 26

// Sensors & Actuators
#define PIN_RAIN_ANALOG 32    // Was 34, changed to match accelometer.ino (32)
#define PIN_BUZZER 5
#define PIN_LED_STRIP 13      // WS2812B Data Pin
#define NUM_LEDS 21           // Total LEDs in strip

// ==========================================
// HAZARD THRESHOLDS
// ==========================================
#define RAIN_THRESHOLD 1000   // Analog value (lower = more water)
#define SEISMIC_THRESHOLD 1.5 // m/s^2 deviation from baseline
#define FIRE_THRESHOLD 50.0   // Degrees Celsius

// ==========================================
// CONFIGURATION
// ==========================================
const long TELEMETRY_INTERVAL = 200; // ms
unsigned long lastTelemetryTime = 0;

// ==========================================
// OBJECTS
// ==========================================
Adafruit_MPU6050 mpu;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
TwoWire FireBus = TwoWire(1); // Secondary I2C bus
Adafruit_NeoPixel strip(NUM_LEDS, PIN_LED_STRIP, NEO_GRB + NEO_KHZ800);

bool mpuFound = false;
bool fireSensorFound = false;

// ==========================================
// LED ZONE MAPPING (COPIED FROM accelometer.ino)
// ==========================================
struct LEDZone {
  int start;
  int count;
  bool fireRed;  // true = RED, false = GREEN during Fire
  bool rainRed;  // true = RED, false = GREEN during Rain
  bool seisRed;  // true = RED, false = GREEN during Seismic
};

struct Building {
  const char* name;
  LEDZone zones[5]; // Max 5 sub-zones per building
  int numZones;
};

// USER: CONFIGURE YOUR HAZARD RESPONSES HERE
// Format: {start, count, fireRed, rainRed, seisRed}
const Building buildings[] = {
  {"Evacuation 1", {{0, 3, false, true, false}}, 1},       // LEDs 0-2 (3 LEDs)
  {"Building 1", {
    {3, 2, false, false, true},  // LEDs 3-4
    {5, 2, false, false, true},  // LEDs 5-6
    {7, 2, false, false, true},  // LEDs 7-8
    {9, 2, false, false, true}   // LEDs 9-10
  }, 4},                                                    // Total: 8 LEDs
  {"Evacuation 2", {{11, 2, true, true, false}}, 1},       // LEDs 11-12 (2 LEDs)
  {"Building 2", {
    {13, 2, false, false, true}, // LEDs 13-14
    {15, 2, true, false, true},  // LEDs 15-16
    {17, 2, false, false, true}, // LEDs 17-18
    {19, 2, false, false, true}  // LEDs 19-20
  }, 4}                                                     // Total: 8 LEDs
};
const int numBuildings = sizeof(buildings) / sizeof(buildings[0]);

// ==========================================
// STATE
// ==========================================
struct SensorState {
  bool fire;
  bool rain;
  bool seismic;
  int rain_level;
  float accel_x;
  float accel_y;
  float accel_z;
  float gyro_x;
  float gyro_y;
  float gyro_z;
};

SensorState currentSensors;
float baselineX = 0, baselineY = 0, baselineZ = 0;
bool mpuFound = false;

// Alert flags for LED system
bool fireAlert = false;
bool rainAlert = false;
bool seismicAlert = false;

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  while(!Serial);
  
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_RAIN_ANALOG, INPUT); // Analog input for rain
  
  delay(1000);

  // 1. Initialize Primary I2C Bus (MPU6050)
  pinMode(I2C_SDA, INPUT); pinMode(I2C_SCL, INPUT);
  delay(10);
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);
  delay(100);

  // 2. Scan for MPU6050
  Wire.beginTransmission(0x68);
  if (Wire.endTransmission() == 0) {
    mpuFound = true;
  } else {
    Wire.beginTransmission(0x69);
    if (Wire.endTransmission() == 0) mpuFound = true;
  }

  if (mpuFound) {
    if (!mpu.begin()) {
      Serial.println("{\"event\":\"error\",\"message\":\"MPU6050 init failed\"}");
      mpuFound = false;
    } else {
      mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
      mpu.setFilterBandwidth(MPU6050_BAND_10_HZ);
    }
  }

  // 3. Initialize Secondary I2C Bus (Fire Sensor)
  FireBus.begin(FIRE_SDA, FIRE_SCL, 100000);
  delay(100);

  // 4. Initialize MLX90614
  if (!mlx.begin(0x5A, &FireBus)) { // Addr 0x5A on FireBus
    Serial.println("{\"event\":\"error\",\"message\":\"MLX90614 init failed\"}");
    fireSensorFound = false;
  } else {
    fireSensorFound = true;
  }

  // 5. Calibrate Baseline (if MPU found)
  if (mpuFound) {
    float sumX = 0, sumY = 0, sumZ = 0;
    for(int i = 0; i < 50; i++) {
        sensors_event_t a, g, t;
        mpu.getEvent(&a, &g, &t);
        sumX += a.acceleration.x;
        sumY += a.acceleration.y;
        sumZ += a.acceleration.z;
        delay(20);
    }
    baselineX = sumX / 50.0;
    baselineY = sumY / 50.0;
    baselineZ = sumZ / 50.0;
  }

  // 6. Initialize LED Strip
  strip.begin();
  strip.setBrightness(50);
  strip.show(); // Initialize all pixels to 'off'

  Serial.println("{\"event\":\"boot\",\"status\":\"ready\"}");
}

// ==========================================
// SENSOR READING
// ==========================================
// ==========================================
// SENSOR READING
// ==========================================
void readSensors() {
  // 1. Fire Sensor (MLX90614 Temp)
  if (fireSensorFound) {
    float objTemp = mlx.readObjectTempC();
    currentSensors.fire = (objTemp > FIRE_THRESHOLD);
    fireAlert = currentSensors.fire;
    
    // Optional: Log temp if high
    if (currentSensors.fire) {
       // logic handled in loop/telemetry
    }
  } else {
    currentSensors.fire = false;
  }

  // 2. Rain Sensor (lower value = more water)
  currentSensors.rain_level = analogRead(PIN_RAIN_ANALOG);
  currentSensors.rain = (currentSensors.rain_level < RAIN_THRESHOLD);
  rainAlert = currentSensors.rain;

  // 3. MPU6050 (Seismic detection)
  if (mpuFound) {
    sensors_event_t a, g, temp;
    if (mpu.getEvent(&a, &g, &temp)) {
      currentSensors.accel_x = a.acceleration.x;
      currentSensors.accel_y = a.acceleration.y;
      currentSensors.accel_z = a.acceleration.z;
      currentSensors.gyro_x = g.gyro.x;
      currentSensors.gyro_y = g.gyro.y;
      currentSensors.gyro_z = g.gyro.z;
      
      // Calculate magnitude deviation from baseline
      float dx = a.acceleration.x - baselineX;
      float dy = a.acceleration.y - baselineY;
      float dz = a.acceleration.z - baselineZ;
      float magnitude = sqrt(dx*dx + dy*dy + dz*dz);
      currentSensors.seismic = (magnitude > SEISMIC_THRESHOLD);
      seismicAlert = currentSensors.seismic;
    }
  }
}

// ==========================================
// JSON TELEMETRY
// ==========================================
void sendTelemetry() {
  StaticJsonDocument<512> doc;
  
  doc["type"] = "telemetry";
  doc["fire"] = currentSensors.fire;
  doc["raining"] = currentSensors.rain_level;
  
  JsonObject accel = doc.createNestedObject("accel");
  accel["x"] = currentSensors.accel_x;
  accel["y"] = currentSensors.accel_y;
  accel["z"] = currentSensors.accel_z;

  JsonObject eq = doc.createNestedObject("earthquake");
  eq["x"] = currentSensors.gyro_x;
  eq["y"] = currentSensors.gyro_y;
  eq["z"] = currentSensors.gyro_z;

  serializeJson(doc, Serial);
  Serial.println();
}

// ==========================================
// LED ANIMATION ENGINE (Local + Server Override)
// ==========================================
void updateLEDs() {
  static unsigned long lastAnimate = 0;
  static int chaseIndex = 0;
  static bool blinkState = false;

  // Check for server override timeout
  if (serverOverride && millis() > serverOverrideTimeout) {
    serverOverride = false;
    digitalWrite(PIN_BUZZER, LOW);
  }
  
  // If server is controlling LEDs, skip local logic
  if (serverOverride) {
    return;
  }

  bool isAnyAlert = (fireAlert || rainAlert || seismicAlert);

  if (isAnyAlert) {
    // HAZARD GUIDANCE MODE
    if (millis() - lastAnimate > 300) {
      blinkState = !blinkState;
      strip.clear();

      for (int b = 0; b < numBuildings; b++) {
        for (int z = 0; z < buildings[b].numZones; z++) {
          LEDZone zone = buildings[b].zones[z];
          
          // Determine color for this zone based on HIGHEST priority alert
          bool shouldBeRed = false;
          if (seismicAlert) shouldBeRed = zone.seisRed;
          else if (fireAlert) shouldBeRed = zone.fireRed;
          else if (rainAlert) shouldBeRed = zone.rainRed;

          uint32_t zoneColor;
          if (shouldBeRed) {
            zoneColor = blinkState ? strip.Color(255, 0, 0) : strip.Color(0, 0, 0);
          } else {
            zoneColor = strip.Color(0, 255, 0); // Safe Zone
          }

          for (int i = zone.start; i < zone.start + zone.count; i++) {
            if (i < NUM_LEDS) strip.setPixelColor(i, zoneColor);
          }
        }
      }
      strip.show();
      lastAnimate = millis();
    }
    
    // Buzzer during hazard
    digitalWrite(PIN_BUZZER, blinkState ? HIGH : LOW);
    
  } else {
    // SAFE FLOW CHASE (GREEN)
    if (millis() - lastAnimate > 150) {
      strip.clear();
      
      // Calculate which zone should be lit
      int globalZoneCounter = 0;
      int targetZone = chaseIndex;

      for (int b = 0; b < numBuildings; b++) {
        for (int z = 0; z < buildings[b].numZones; z++) {
          if (globalZoneCounter == targetZone) {
            // Light up this zone
            int start = buildings[b].zones[z].start;
            int count = buildings[b].zones[z].count;
            for (int i = start; i < start + count; i++) {
              if (i < NUM_LEDS) strip.setPixelColor(i, strip.Color(0, 255, 0));
            }
          }
          globalZoneCounter++;
        }
      }
      
      strip.show();
      chaseIndex = (chaseIndex + 1) % globalZoneCounter; // Cycle through all zones
      lastAnimate = millis();
    }
    
    digitalWrite(PIN_BUZZER, LOW);
  }
}

// ==========================================
// COMMAND HANDLER (Server-Controlled LEDs)
// ==========================================
// Server override mode - when enabled, local sensor-based LED control is disabled
bool serverOverride = false;
unsigned long serverOverrideTimeout = 0;

void handleCommand(String input) {
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, input);

  if (error) return;

  const char* cmd = doc["cmd"];
  
  // --- Basic Commands ---
  if (strcmp(cmd, "set_alert") == 0) {
    int alertLevel = doc["alert"];
    Serial.print("{\"event\":\"alert_set\",\"alert\":");
    Serial.print(alertLevel);
    Serial.println("}");
  }
  else if (strcmp(cmd, "ping") == 0) {
    Serial.print("{\"event\":\"pong\",\"uptime\":");
    Serial.print(millis());
    Serial.println("}");
  }
  
  // --- LED Path Control (AI-Driven Evacuation) ---
  // Command: {"cmd":"set_path","path":[0,1,3],"hazards":[2,4]}
  // path = zone indices to light GREEN (safe route)
  // hazards = zone indices to light RED (danger)
  else if (strcmp(cmd, "set_path") == 0) {
    serverOverride = true;
    serverOverrideTimeout = millis() + 10000; // 10s timeout, then revert to local
    
    strip.clear();
    
    // Get total zone count for bounds checking
    int totalZones = 0;
    for (int b = 0; b < numBuildings; b++) {
      totalZones += buildings[b].numZones;
    }
    
    // Light up safe path (GREEN)
    JsonArray pathArray = doc["path"];
    for (int zoneIdx : pathArray) {
      if (zoneIdx >= 0 && zoneIdx < totalZones) {
        int counter = 0;
        for (int b = 0; b < numBuildings; b++) {
          for (int z = 0; z < buildings[b].numZones; z++) {
            if (counter == zoneIdx) {
              LEDZone zone = buildings[b].zones[z];
              for (int i = zone.start; i < zone.start + zone.count && i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.Color(0, 255, 0)); // GREEN
              }
            }
            counter++;
          }
        }
      }
    }
    
    // Mark hazards (RED blinking handled in loop)
    JsonArray hazardArray = doc["hazards"];
    for (int zoneIdx : hazardArray) {
      if (zoneIdx >= 0 && zoneIdx < totalZones) {
        int counter = 0;
        for (int b = 0; b < numBuildings; b++) {
          for (int z = 0; z < buildings[b].numZones; z++) {
            if (counter == zoneIdx) {
              LEDZone zone = buildings[b].zones[z];
              for (int i = zone.start; i < zone.start + zone.count && i < NUM_LEDS; i++) {
                strip.setPixelColor(i, strip.Color(255, 0, 0)); // RED
              }
            }
            counter++;
          }
        }
      }
    }
    
    strip.show();
    digitalWrite(PIN_BUZZER, hazardArray.size() > 0 ? HIGH : LOW);
    
    Serial.println("{\"event\":\"path_set\",\"status\":\"ok\"}");
  }
  
  // --- Direct LED Control (Per-LED) ---
  // Command: {"cmd":"set_leds","leds":[{"i":0,"r":255,"g":0,"b":0},{"i":1,"r":0,"g":255,"b":0}]}
  else if (strcmp(cmd, "set_leds") == 0) {
    serverOverride = true;
    serverOverrideTimeout = millis() + 10000;
    
    JsonArray ledsArray = doc["leds"];
    for (JsonObject led : ledsArray) {
      int i = led["i"];
      int r = led["r"];
      int g = led["g"];
      int b = led["b"];
      if (i >= 0 && i < NUM_LEDS) {
        strip.setPixelColor(i, strip.Color(r, g, b));
      }
    }
    strip.show();
    
    Serial.println("{\"event\":\"leds_set\",\"status\":\"ok\"}");
  }
  
  // --- Release Server Control ---
  // Command: {"cmd":"release_leds"}
  else if (strcmp(cmd, "release_leds") == 0) {
    serverOverride = false;
    digitalWrite(PIN_BUZZER, LOW);
    Serial.println("{\"event\":\"leds_released\",\"status\":\"ok\"}");
  }
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
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
  
  // 3. Update LED Strip (runs every loop for smooth animation)
  updateLEDs();
}
