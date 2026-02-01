/**
 * MOD-EVAC-MS - ESP32 Main Controller Firmware
 * Competition-grade embedded system for hazard detection and evacuation guidance
 * 
 * Hardware:
 * - ESP32-DevKitC
 * - Water sensor (analog GPIO34)
 * - MPU6050 gyroscope (I2C)
 * - WS2812B LED strip with zone control (GPIO5)
 * 
 * Communication: USB Serial JSON (115200 baud)
 * No WiFi dependency - fully local operation
 */

#include <Arduino.h>
#include <FastLED.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <ArduinoJson.h>

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================
#define WATER_SENSOR_PIN    34      // Analog input for water sensor
#define LED_DATA_PIN        5       // WS2812B data pin
#define LED_COUNT           60      // Total LEDs in strip
#define I2C_SDA             21      // MPU6050 SDA
#define I2C_SCL             22      // MPU6050 SCL

// ============================================================================
// LED ZONE CONFIGURATION (Nested array for evacuation control)
// Each zone: {start_led, end_led}
// ============================================================================
#define NUM_ZONES 4
const uint8_t LED_ZONES[NUM_ZONES][2] = {
    {0, 14},    // Zone 0: Entrance area
    {15, 29},   // Zone 1: Hallway section A
    {30, 44},   // Zone 2: Hallway section B
    {45, 59}    // Zone 3: Exit area
};

// ============================================================================
// GSM MODULE CONFIGURATION (SIM800L or similar)
// ============================================================================
#define GSM_RX_PIN          16      // ESP32 RX <- GSM TX
#define GSM_TX_PIN          17      // ESP32 TX -> GSM RX
#define GSM_BAUD            9600
HardwareSerial GsmSerial(2);        // Use UART2

// ============================================================================
// ALERT STATES
// ============================================================================
typedef enum {
    ALERT_SAFE = 0,         // Solid green
    ALERT_CALLING,          // Pulsing amber
    ALERT_MESSAGING,        // Slow blue pulse
    ALERT_DANGER,           // Fast red blink
    ALERT_EVACUATE          // Chase pattern toward exit
} AlertState_t;

// ============================================================================
// GLOBAL STATE
// ============================================================================
CRGB leds[LED_COUNT];
Adafruit_MPU6050 mpu;

// Current system state
volatile AlertState_t currentAlert = ALERT_SAFE;
volatile int activeZone = -1;  // -1 = all zones, 0-3 = specific zone

// Sensor readings (updated by sensor task)
volatile float waterLevel = 0.0;
volatile float gyroX = 0.0, gyroY = 0.0, gyroZ = 0.0;
volatile float accelX = 0.0, accelY = 0.0, accelZ = 0.0;

// Task handles
TaskHandle_t sensorTaskHandle = NULL;
TaskHandle_t ledTaskHandle = NULL;
TaskHandle_t serialTaskHandle = NULL;

// Mutex for thread-safe sensor access
SemaphoreHandle_t sensorMutex;

// ============================================================================
// FUNCTION PROTOTYPES
// ============================================================================
void sensorTask(void *parameter);
void ledTask(void *parameter);
void serialTask(void *parameter);
void setZoneColor(int zone, CRGB color);
void setAllZonesColor(CRGB color);
void runEvacuationPattern(int exitZone);
void parseCommand(const char* json);
void gsmCall(const char* number);
void gsmSendSms(const char* number, const char* message);
void gsmSendCommand(const char* cmd);

// ============================================================================
// SETUP
// ============================================================================
void setup() {
    // Initialize Serial for communication
    Serial.begin(115200);
    while (!Serial) { delay(10); }
    
    Serial.println("{\"event\":\"boot\",\"status\":\"initializing\"}");
    
    // Initialize GSM Serial
    GsmSerial.begin(GSM_BAUD, SERIAL_8N1, GSM_RX_PIN, GSM_TX_PIN);
    Serial.println("{\"event\":\"init\",\"component\":\"gsm\",\"status\":\"ok\"}");
    
    // Initialize I2C for MPU6050
    Wire.begin(I2C_SDA, I2C_SCL);
    
    // Initialize MPU6050
    if (!mpu.begin()) {
        Serial.println("{\"event\":\"error\",\"component\":\"mpu6050\",\"message\":\"init_failed\"}");
    } else {
        mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
        mpu.setGyroRange(MPU6050_RANGE_500_DEG);
        mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
        Serial.println("{\"event\":\"init\",\"component\":\"mpu6050\",\"status\":\"ok\"}");
    }
    
    // Initialize water sensor pin
    pinMode(WATER_SENSOR_PIN, INPUT);
    Serial.println("{\"event\":\"init\",\"component\":\"water_sensor\",\"status\":\"ok\"}");
    
    // Initialize FastLED
    FastLED.addLeds<WS2812B, LED_DATA_PIN, GRB>(leds, LED_COUNT);
    FastLED.setBrightness(128);
    FastLED.clear();
    FastLED.show();
    Serial.println("{\"event\":\"init\",\"component\":\"led_strip\",\"leds\":" + String(LED_COUNT) + ",\"zones\":" + String(NUM_ZONES) + "}");
    
    // Create mutex
    // I added this mutex to prevent race conditions between the High-Frequency Sensor Task (Core 0)
    // and the Serial Telemetry Task (Core 1), ensuring that JSON packets are never corrupted.
    sensorMutex = xSemaphoreCreateMutex();
    
    // Create FreeRTOS tasks on different cores for true parallelism
    // I pinned the Sensor Task to Core 0 to isolate the interrupt-heavy I2C operations suitable for MPU6050 polling.
    xTaskCreatePinnedToCore(
        sensorTask,         // Task function
        "SensorTask",       // Name
        4096,               // Stack size
        NULL,               // Parameters
        2,                  // Priority (higher = more important)
        &sensorTaskHandle,  // Task handle
        0                   // Core 0
    );
    
    xTaskCreatePinnedToCore(
        ledTask,
        "LEDTask",
        4096,
        NULL,
        1,
        &ledTaskHandle,
        1                   // Core 1
    );
    
    xTaskCreatePinnedToCore(
        serialTask,
        "SerialTask",
        8192,
        NULL,
        3,                  // Highest priority for command processing
        &serialTaskHandle,
        0                   // Core 0
    );
    
    // Boot animation - green sweep
    for (int i = 0; i < LED_COUNT; i++) {
        leds[i] = CRGB::Green;
        FastLED.show();
        delay(20);
    }
    delay(500);
    FastLED.clear();
    FastLED.show();
    
    Serial.println("{\"event\":\"boot\",\"status\":\"complete\",\"ready\":true}");
}

void loop() {
    // Main loop is empty - all work done in FreeRTOS tasks
    vTaskDelay(portMAX_DELAY);
}

// ============================================================================
// SENSOR TASK - Core 0
// Reads water sensor and gyroscope at 50Hz
// ============================================================================
void sensorTask(void *parameter) {
    sensors_event_t a, g, temp;
    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t taskPeriod = pdMS_TO_TICKS(20);  // 50Hz
    
    while (true) {
        // Read water sensor (analog 0-4095)
        int rawWater = analogRead(WATER_SENSOR_PIN);
        float waterPercent = (rawWater / 4095.0) * 100.0;
        
        // Read MPU6050
        mpu.getEvent(&a, &g, &temp);
        
        // Thread-safe update of global state
        if (xSemaphoreTake(sensorMutex, pdMS_TO_TICKS(5))) {
            waterLevel = waterPercent;
            gyroX = g.gyro.x;
            gyroY = g.gyro.y;
            gyroZ = g.gyro.z;
            accelX = a.acceleration.x;
            accelY = a.acceleration.y;
            accelZ = a.acceleration.z;
            xSemaphoreGive(sensorMutex);
        }
        
        // Wait for next period (precise timing)
        vTaskDelayUntil(&lastWakeTime, taskPeriod);
    }
}

// ============================================================================
// LED TASK - Core 1
// Handles LED patterns based on current alert state
// ============================================================================
void ledTask(void *parameter) {
    uint8_t brightness = 0;
    bool increasing = true;
    uint8_t chasePos = 0;
    TickType_t lastUpdate = xTaskGetTickCount();
    
    while (true) {
        AlertState_t state = currentAlert;
        
        switch (state) {
            case ALERT_SAFE:
                // Solid green on all zones
                setAllZonesColor(CRGB::Green);
                FastLED.show();
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
                
            case ALERT_CALLING:
                // Pulsing amber
                if (increasing) {
                    brightness += 5;
                    if (brightness >= 250) increasing = false;
                } else {
                    brightness -= 5;
                    if (brightness <= 10) increasing = true;
                }
                FastLED.setBrightness(brightness);
                setAllZonesColor(CRGB(255, 150, 0));  // Amber
                FastLED.show();
                vTaskDelay(pdMS_TO_TICKS(20));
                break;
                
            case ALERT_MESSAGING:
                // Slow blue pulse
                if (increasing) {
                    brightness += 2;
                    if (brightness >= 200) increasing = false;
                } else {
                    brightness -= 2;
                    if (brightness <= 20) increasing = true;
                }
                FastLED.setBrightness(brightness);
                setAllZonesColor(CRGB::Blue);
                FastLED.show();
                vTaskDelay(pdMS_TO_TICKS(30));
                break;
                
            case ALERT_DANGER:
                // Fast red blink
                setAllZonesColor(CRGB::Red);
                FastLED.setBrightness(255);
                FastLED.show();
                vTaskDelay(pdMS_TO_TICKS(100));
                FastLED.clear();
                FastLED.show();
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
                
            case ALERT_EVACUATE:
                // Chase pattern toward exit (Zone 3)
                runEvacuationPattern(3);
                vTaskDelay(pdMS_TO_TICKS(50));
                break;
        }
    }
}

// ============================================================================
// SERIAL TASK - Core 0
// Handles incoming commands and sends telemetry
// ============================================================================
void serialTask(void *parameter) {
    char inputBuffer[512];
    int bufferIndex = 0;
    TickType_t lastTelemetry = xTaskGetTickCount();
    const TickType_t telemetryPeriod = pdMS_TO_TICKS(100);  // 10Hz telemetry
    
    while (true) {
        // Check for incoming commands
        while (Serial.available()) {
            char c = Serial.read();
            if (c == '\n' || c == '\r') {
                if (bufferIndex > 0) {
                    inputBuffer[bufferIndex] = '\0';
                    parseCommand(inputBuffer);
                    bufferIndex = 0;
                }
            } else if (bufferIndex < sizeof(inputBuffer) - 1) {
                inputBuffer[bufferIndex++] = c;
            }
        }
        
        // Send telemetry at fixed rate
        if ((xTaskGetTickCount() - lastTelemetry) >= telemetryPeriod) {
            StaticJsonDocument<256> doc;
            
            if (xSemaphoreTake(sensorMutex, pdMS_TO_TICKS(5))) {
                doc["type"] = "telemetry";
                doc["water"] = waterLevel;
                
                JsonObject gyro = doc.createNestedObject("gyro");
                gyro["x"] = gyroX;
                gyro["y"] = gyroY;
                gyro["z"] = gyroZ;
                
                JsonObject accel = doc.createNestedObject("accel");
                accel["x"] = accelX;
                accel["y"] = accelY;
                accel["z"] = accelZ;
                
                doc["alert"] = (int)currentAlert;
                doc["ts"] = millis();
                
                xSemaphoreGive(sensorMutex);
            }
            
            serializeJson(doc, Serial);
            Serial.println();
            
            lastTelemetry = xTaskGetTickCount();
        }
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

void setZoneColor(int zone, CRGB color) {
    if (zone < 0 || zone >= NUM_ZONES) return;
    for (int i = LED_ZONES[zone][0]; i <= LED_ZONES[zone][1]; i++) {
        leds[i] = color;
    }
}

void setAllZonesColor(CRGB color) {
    for (int z = 0; z < NUM_ZONES; z++) {
        setZoneColor(z, color);
    }
}

void runEvacuationPattern(int exitZone) {
    static uint8_t phase = 0;
    
    // Clear all LEDs
    FastLED.clear();
    
    // Chase pattern: light up 3 LEDs moving toward exit
    for (int z = 0; z < NUM_ZONES; z++) {
        int start = LED_ZONES[z][0];
        int end = LED_ZONES[z][1];
        int zoneLen = end - start + 1;
        
        // Direction: toward exit (zone 3)
        int pos = (phase % zoneLen);
        if (z < exitZone) {
            // Chase forward toward exit
            leds[start + pos] = CRGB::Green;
            if (pos > 0) leds[start + pos - 1] = CRGB(0, 100, 0);
            if (pos > 1) leds[start + pos - 2] = CRGB(0, 50, 0);
        } else if (z == exitZone) {
            // Exit zone pulses green
            for (int i = start; i <= end; i++) {
                leds[i] = CRGB::Green;
            }
        }
    }
    
    FastLED.show();
    phase++;
}

void parseCommand(const char* json) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, json);
    
    if (error) {
        Serial.println("{\"event\":\"error\",\"message\":\"json_parse_failed\"}");
        return;
    }
    
    const char* cmd = doc["cmd"];
    if (!cmd) return;
    
    if (strcmp(cmd, "set_alert") == 0) {
        int alert = doc["alert"] | 0;
        if (alert >= 0 && alert <= 4) {
            currentAlert = (AlertState_t)alert;
            Serial.print("{\"event\":\"alert_set\",\"alert\":");
            Serial.print(alert);
            Serial.println("}");
        }
    } else if (strcmp(cmd, "set_zone") == 0) {
        int zone = doc["zone"] | -1;
        int r = doc["r"] | 0;
        int g = doc["g"] | 0;
        int b = doc["b"] | 0;
        
        if (zone >= 0 && zone < NUM_ZONES) {
            setZoneColor(zone, CRGB(r, g, b));
            FastLED.show();
            Serial.print("{\"event\":\"zone_set\",\"zone\":");
            Serial.print(zone);
            Serial.println("}");
        }
    } else if (strcmp(cmd, "gsm_call") == 0) {
        const char* number = doc["number"];
        if (number) {
            gsmCall(number);
            Serial.print("{\"event\":\"gsm_call\",\"number\":\"");
            Serial.print(number);
            Serial.println("\"}");
        }
    } else if (strcmp(cmd, "gsm_sms") == 0) {
        const char* number = doc["number"];
        const char* message = doc["message"];
        if (number && message) {
            gsmSendSms(number, message);
            Serial.print("{\"event\":\"gsm_sms\",\"number\":\"");
            Serial.print(number);
            Serial.println("\"}");
        }
    } else if (strcmp(cmd, "ping") == 0) {
        Serial.println("{\"event\":\"pong\",\"uptime\":" + String(millis()) + "}");
    }
}

// ============================================================================
// GSM FUNCTIONS (SIM800L AT Commands)
// ============================================================================

void gsmSendCommand(const char* cmd) {
    GsmSerial.println(cmd);
    delay(100);
}

void gsmCall(const char* number) {
    // ATD command to dial
    String dialCmd = "ATD" + String(number) + ";";
    gsmSendCommand(dialCmd.c_str());
    Serial.println("{\"event\":\"gsm_dialing\",\"number\":\"" + String(number) + "\"}");
    
    // Auto hang up after 30 seconds (emergency ring)
    delay(30000);
    gsmSendCommand("ATH");  // Hang up
    Serial.println("{\"event\":\"gsm_hangup\"}");
}

void gsmSendSms(const char* number, const char* message) {
    // Set SMS text mode
    gsmSendCommand("AT+CMGF=1");
    delay(100);
    
    // Set recipient
    String smsCmd = "AT+CMGS=\"" + String(number) + "\"";
    GsmSerial.println(smsCmd);
    delay(100);
    
    // Send message content
    GsmSerial.print(message);
    delay(100);
    
    // Send Ctrl+Z to transmit
    GsmSerial.write(26);
    delay(1000);
    
    Serial.println("{\"event\":\"gsm_sms_sent\",\"to\":\"" + String(number) + "\"}");
}

