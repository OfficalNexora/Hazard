#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

// I2C Pins (Primary - Seismic)
#define I2C_SDA 21
#define I2C_SCL 22

// I2C Pins (Secondary - Fire)
#define FIRE_SDA 25
#define FIRE_SCL 26

// Rain Sensor Pin (Digital)
#define WATER_PIN 32

// LED Strip (WS2812B)
#define LED_PIN    13
#define NUM_LEDS   21  // Total LEDs (3+8+2+8 = 21)

// I2C Addresses
#define MPU_ADDR      0x68
#define MPU_ADDR_ALT  0x69
#define MLX_ADDR      0x5A

// Level Thresholds (m/s^2) - Lowered for better building feel
#define LVL_1_VIBRATION 1.5   
#define LVL_2_STRONG    4.0
#define LVL_3_SEVERE    8.0

// Rain Threshold (Analog 0-4095 - Lower = More Water)
#define RAIN_THRESHOLD  1000 

// Fire Threshold (°C)
#define FIRE_THRESHOLD  50.0

// Timing (ms)
#define BUMP_FILTER_MS 200 // Slightly shorter filter

Adafruit_MPU6050 mpu;

// Baseline values to ignore gravity/tilt
float baselineX = 0;
float baselineY = 0;
float baselineZ = 0;

// Status Flags
bool mpuFound = false;
bool fireSensorFound = false;
byte mpuAddress = MPU_ADDR;

// Hardware Bus Definitions
TwoWire FireBus = TwoWire(1); // Use second I2C hardware bus
Adafruit_MLX90614 mlx = Adafruit_MLX90614(); 

// LED Controller
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// --- BUILDING LED MAPPING (NESTED ARRAY) ---
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

// --- TINKER-FRIENDLY RESPONSE ENGINE ---
bool fireAlert = false;
bool rainAlert = false;
bool seismicAlert = false;

// Response Logic Prototypes
void handleFireResponse(float temp);
void handleRainResponse(int val);
void handleSeismicResponse(float mag);
void updateLEDs();

void setup() {
  Serial.begin(115200);
  while(!Serial);
  
  pinMode(WATER_PIN, INPUT_PULLUP);
  
  delay(2000);

  // 1. Initialize Primary I2C Bus (MPU6050)
  pinMode(I2C_SDA, INPUT); pinMode(I2C_SCL, INPUT);
  delay(10);
  int sdaState = digitalRead(I2C_SDA);
  int sclState = digitalRead(I2C_SCL);
  if (sdaState == LOW || sclState == LOW) {
    Serial.println("{\"event\":\"error\",\"message\":\"I2C bus stuck LOW\"}");
  }

  Wire.end();
  Wire.setPins(I2C_SDA, I2C_SCL); 
  Wire.begin();
  Wire.setClock(10000);
  delay(100);

  // 2. Scan for MPU6050
  for(byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (addr == 0x68 || addr == 0x69) {
        mpuAddress = addr;
        mpuFound = true;
      }
    }
  }

  if (mpuFound) {
    if (!mpu.begin(mpuAddress)) {
      Serial.println("{\"event\":\"error\",\"message\":\"MPU6050 init failed\"}");
      mpuFound = false;
    } else {
      mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
      mpu.setFilterBandwidth(MPU6050_BAND_10_HZ);
    }
  }

  // 3. Initialize Secondary I2C Bus (Fire Sensor)
  FireBus.begin(FIRE_SDA, FIRE_SCL, 10000);
  delay(100);

  // 4. Fallback: Check Fire Bus for MPU6050
  if (!mpuFound) {
    FireBus.beginTransmission(0x68);
    if (FireBus.endTransmission() == 0) {
      mpuAddress = 0x68;
      if (mpu.begin(0x68, &FireBus)) mpuFound = true;
    }
    if (!mpuFound) {
      FireBus.beginTransmission(0x69);
      if (FireBus.endTransmission() == 0) {
        mpuAddress = 0x69;
        if (mpu.begin(0x69, &FireBus)) mpuFound = true;
      }
    }
  }

  // 5. Scan for MLX90614
  FireBus.beginTransmission(MLX_ADDR);
  if (FireBus.endTransmission() == 0) {
    if (!mlx.begin(MLX_ADDR, &FireBus)) { 
      Serial.println("{\"event\":\"error\",\"message\":\"MLX90614 init failed\"}");
      fireSensorFound = false;
    } else {
      fireSensorFound = true;
    }
  } else {
    fireSensorFound = false;
  }

  // 6. Capture Baseline (Only if MPU found)
  if (mpuFound) {
    float sumX = 0, sumY = 0, sumZ = 0;
    for(int i=0; i<50; i++) {
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
  
  // 7. Initialize LED Strip
  strip.begin();
  strip.setBrightness(50);
  for(int i=0; i<NUM_LEDS; i++) strip.setPixelColor(i, strip.Color(0, 255, 0));
  strip.show();
  
  Serial.println("{\"event\":\"boot\",\"status\":\"ready\"}");
}

unsigned long shakeStartTime = 0;
bool isShaking = false;
float maxMagnitudeThisEvent = 0;
unsigned long lastLivePrint = 0;

void loop() {
  // --- SEISMIC MONITORING ---
  float magnitude = 0;
  if (mpuFound) {
    sensors_event_t a, g, t;
    mpu.getEvent(&a, &g, &t);
    
    float relX = a.acceleration.x - baselineX;
    float relY = a.acceleration.y - baselineY;
    float relZ = a.acceleration.z - baselineZ;
    
    // 3D Magnitude calculation (Industrial Standard)
    magnitude = sqrt(relX*relX + relY*relY + relZ*relZ);
  }

  // --- FIRE MONITORING (Dedicated Pins 25/26) ---
  static unsigned long lastFireCheck = 0;
  if (fireSensorFound && (millis() - lastFireCheck > 1000)) { 
    float objTemp = mlx.readObjectTempC();
    
    // Check for Fire Alert
    if (objTemp > FIRE_THRESHOLD) {
      handleFireResponse(objTemp);
      fireAlert = true;
    } else {
      fireAlert = false;
    }
    
    lastFireCheck = millis();
  }

  // --- RAIN MONITORING (GPIO 32 - ANALOG MODE) ---
  static int rainConsensus = 0;
  static bool filteredIsRaining = false;
  
  int analogRain = analogRead(WATER_PIN); 
  
  // INSTANT-KILL Logic: If electrically dry (>2500), kill YES state immediately
  if (analogRain > 2500) { // Lowered for faster reset
    rainConsensus = 0;
    filteredIsRaining = false;
    rainAlert = false;
  } else {
    // Normal Filtering
    bool rawRain = (analogRain < RAIN_THRESHOLD);
    if (rawRain) {
      if (rainConsensus < 5) rainConsensus++;
    } else {
      if (rainConsensus > 0) rainConsensus--;
    }
    
    // FAST: Trigger 4/5 (~80ms) - Eliminated delay
    if (rainConsensus >= 4) filteredIsRaining = true;
    if (rainConsensus <= 1) filteredIsRaining = false;
  }
  
  if (filteredIsRaining) {
    handleRainResponse(analogRain);
    rainAlert = true;
  }

  // JSON TELEMETRY (Every 200ms)
  if (millis() - lastLivePrint > 200) {
    StaticJsonDocument<256> doc;
    doc["type"] = "telemetry";
    doc["fire"] = fireAlert;
    doc["raining"] = analogRead(WATER_PIN);
    
    JsonObject accel = doc.createNestedObject("accel");
    if (mpuFound) {
      sensors_event_t a, g, t;
      mpu.getEvent(&a, &g, &t);
      accel["x"] = a.acceleration.x;
      accel["y"] = a.acceleration.y;
      accel["z"] = a.acceleration.z;
    } else {
      accel["x"] = 0; accel["y"] = 0; accel["z"] = 0;
    }
    
    JsonObject eq = doc.createNestedObject("earthquake");
    eq["x"] = magnitude;
    eq["y"] = 0;
    eq["z"] = 0;
    
    serializeJson(doc, Serial);
    Serial.println();
    lastLivePrint = millis();
  }

  // Detection logic
  if (magnitude > LVL_1_VIBRATION) {
    if (!isShaking) {
      shakeStartTime = millis();
      isShaking = true;
      maxMagnitudeThisEvent = 0;
    }
    
    if (magnitude > maxMagnitudeThisEvent) {
      maxMagnitudeThisEvent = magnitude;
    }
    seismicAlert = true;
  } else {
    if (isShaking) {
      unsigned long duration = millis() - shakeStartTime;
      if (duration > BUMP_FILTER_MS) {
        int level = 1;
        if (maxMagnitudeThisEvent > LVL_3_SEVERE) level = 3;
        else if (maxMagnitudeThisEvent > LVL_2_STRONG) level = 2;
        
        StaticJsonDocument<128> doc;
        doc["event"] = "earthquake";
        doc["level"] = level;
        doc["duration"] = duration;
        doc["peak"] = maxMagnitudeThisEvent;
        serializeJson(doc, Serial);
        Serial.println();
      }
      isShaking = false;
    }
    seismicAlert = false;
  }

  // --- LED STATUS UPDATER ---
  updateLEDs();

  delay(20); // Faster sampling
}

// ==========================================
// RESPONSE HANDLERS (JSON OUTPUT)
// ==========================================

void handleFireResponse(float temp) {
  static unsigned long lastSerial = 0;
  if (millis() - lastSerial > 5000) {
    StaticJsonDocument<96> doc;
    doc["event"] = "fire_alert";
    doc["temp"] = temp;
    serializeJson(doc, Serial);
    Serial.println();
    lastSerial = millis();
  }
}

void handleRainResponse(int val) {
  static unsigned long lastSerial = 0;
  if (millis() - lastSerial > 5000) {
    StaticJsonDocument<96> doc;
    doc["event"] = "rain_alert";
    doc["value"] = val;
    serializeJson(doc, Serial);
    Serial.println();
    lastSerial = millis();
  }
}

void handleSeismicResponse(float mag) {
  // Handled in main loop
}

// ==========================================
// LED ANIMATION ENGINE (RED/GREEN)
// ==========================================
void updateLEDs() {
  static unsigned long lastAnimate = 0;
  static int chaseIndex = 0;
  static bool blinkState = false;

  bool isAnyAlert = (fireAlert || rainAlert || seismicAlert);

  if (isAnyAlert) {
    // 🚨 HAZARD GUIDANCE MODE
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
  } else {
    // 🏃 SAFE FLOW CHASE (GREEN)
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
  }
}
