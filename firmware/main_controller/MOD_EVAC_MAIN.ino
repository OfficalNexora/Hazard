#include <Adafruit_NeoPixel.h>
#include <Arduino.h>
#include <ArduinoJson.h> // Required for JSON serialization
#include <DNSServer.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WiFiUdp.h>
#include <Wire.h>

/* ================= CONFIG ================= */
#define PIN_LED_STRIP 17
#define NUM_LEDS 19
#define PIN_BUZZER 5

#define FIRE_PIN 25         // IR flame sensor (LOW = fire)
#define RAIN_PIN 34         // Analog rain sensor (Value: 0-4095)
#define RAIN_THRESHOLD 1200 // Lowered to reduce false positives from noise

#define SDA_PIN 21
#define SCL_PIN 22
#define MPU_ADDR 0x68

#define SEISMIC_THRESHOLD 1.5
#define POLLING_INTERVAL 100 // 10Hz polling = Prevents Heat & I2C congestion

#define CONFIRM_TIME 2000 // 2 seconds to confirm hazard
#define ABORT_TIME 3000   // 3 seconds to clear hazard
#define BLINK_TIME 500
#define DISCOVERY_PORT 8002
#define DISCOVERY_CHECK_INTERVAL 2000

/*  LED ================= */
Adafruit_NeoPixel strip(NUM_LEDS, PIN_LED_STRIP, NEO_GRB + NEO_KHZ800);
WebServer server(80);
Preferences preferences;
DNSServer dnsServer;

// WiFi Config
String savedSSID = "";
String savedPassword = "";
String serverBase = ""; // e.g., "192.168.1.100" or "http://tunnel.com"
bool isConfigured = false;
bool isAPMode = true;
String macAddress = "";
const String AP_SSID_PREFIX = "HAZARD_ROBOT_";
String deviceName = "Robot_Main";

bool mpuFound = false;

/* ================= LED GROUPS (Physical 0-18 Mapping) ================= */
int indicator[] = {0};
int evac1[] = {1, 2, 3};
int b1_f1_left[] = {4, 5};
int b1_f1_right[] = {6, 7};
int b1_f2_right[] = {8, 9};
int b1_f2_left[] = {10, 11};
int evac2[] = {12, 13, 14};
int b2_path[] = {15, 16};
int b2_fire_mark[] = {17, 18};

int b1_all[] = {4, 5, 6, 7, 8, 9, 10, 11};

/* ================= STATE ================= */
bool fireActive = false;
bool rainActive = false;
bool seismicActive = false;
bool serverOverride = false;

unsigned long fireLastDetect = 0;
unsigned long rainLastDetect = 0;
unsigned long seismicLastDetect = 0;

#define LATCH_TIME 3000 // 3 seconds "Slow Release" latch

unsigned long lastPollTime = 0;
unsigned long blinkTimer = 0;
unsigned long lastDiscoveryCheck = 0;
bool blinkState = false;
WiFiUDP udp;

struct {
  float ax, ay, az;
  int rain_raw;
} sensors_data;

float baseX = 0, baseY = 0, baseZ = 0;

/* ================= HELPERS ================= */
void clearAll() { strip.clear(); }

void setGroup(int *grp, int len, uint32_t c) {
  for (int i = 0; i < len; i++)
    strip.setPixelColor(grp[i], c);
}

// ============================================================================
// HELPERS
// ============================================================================
String getJsonValue(String json, String key) {
  String searchKey = "\"" + key + "\":\"";
  int start = json.indexOf(searchKey);
  if (start == -1)
    return "";
  start += searchKey.length();
  int end = json.indexOf("\"", start);
  if (end == -1)
    return "";
  return json.substring(start, end);
}

void loadConfig() {
  preferences.begin("hazard", true);
  savedSSID = preferences.getString("ssid", "");
  savedPassword = preferences.getString("pass", "");
  serverBase = preferences.getString("server", "");
  deviceName = preferences.getString("name", "Robot_Main");
  isConfigured = preferences.getBool("configured", false);
  preferences.end();
}

// ============================================================================
// HTTP HANDLERS
// ============================================================================
void handleStatus() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  String json = "{";
  json += "\"type\":\"robot_main\",";
  json += "\"name\":\"" + deviceName + "\",";
  json += "\"configured\":" + String(isConfigured ? "true" : "false") + ",";
  json += "\"mode\":\"" + String(isAPMode ? "ap" : "client") + "\",";
  json += "\"ip\":\"" +
          (isAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) +
          "\"";
  json += "}";
  server.send(200, "application/json", json);
}

void handleConfigure() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "POST,GET,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");

  if (server.method() == HTTP_OPTIONS) {
    server.send(204);
    return;
  }

  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"status\":\"error\"}");
    return;
  }

  String body = server.arg("plain");
  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(400, "application/json",
                "{\"status\":\"error\",\"message\":\"Invalid JSON\"}");
    return;
  }

  savedSSID = doc["ssid"] | "";
  savedPassword = doc["password"] | "";
  serverBase = doc["server_ip"] | (const char *)doc["server"] | "";
  deviceName = doc["name"] | "";

  if (deviceName == "")
    deviceName = "Robot_" + macAddress.substring(macAddress.length() - 4);

  preferences.begin("hazard", false);
  preferences.putString("ssid", savedSSID);
  preferences.putString("pass", savedPassword);
  preferences.putString("server", serverBase);
  preferences.putString("name", deviceName);
  preferences.putBool("configured", true);
  preferences.end();

  server.send(200, "application/json",
              "{\"status\":\"ok\",\"msg\":\"Config saved. Rebooting...\"}");
  delay(1000);
  ESP.restart();
}

// ============================================================================
// SERVER DISCOVERY LISTENER
// ============================================================================
void checkServerDiscovery() {
  // Listen for server announcement broadcasts
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    char buffer[512];
    int len = udp.read(buffer, sizeof(buffer) - 1);
    if (len > 0) {
      buffer[len] = '\0';

      // Parse the JSON announcement
      DynamicJsonDocument doc(512);
      DeserializationError error = deserializeJson(doc, buffer);

      if (!error && doc["type"] == "server_announce") {
        String newIP = doc["ip"] | "";
        String tunnelUrl = doc["tunnel"] | "";
        int apiPort = doc["api_port"] | 8000;

        // Prefer tunnel URL if available (for cloud access)
        String newServer = "";
        if (tunnelUrl.length() > 0) {
          newServer = tunnelUrl;
        } else if (newIP.length() > 0) {
          newServer = "http://" + newIP + ":" + String(apiPort);
        }

        // Update server if changed
        if (newServer.length() > 0 && newServer != serverBase) {
          Serial.println("DISCOVERY:Server updated to: " + newServer);
          serverBase = newServer;

          // Save to preferences
          preferences.begin("hazard", false);
          preferences.putString("server", serverBase);
          preferences.end();
        }
      }
    }
  }
}

void blinkBuilding1() {
  if (millis() - blinkTimer > BLINK_TIME) {
    blinkTimer = millis();
    blinkState = !blinkState;
  }
  uint32_t c = blinkState ? strip.Color(255, 0, 0) : strip.Color(0, 150, 0);
  setGroup(b1_all, 8, c);
}

/* ================= SENSOR READ ================= */
void readSensors() {
  unsigned long now = millis();

  // 1. Fire Sensor (Digital IR) - Fast Trigger, Slow Release
  if (digitalRead(FIRE_PIN) == LOW) {
    fireLastDetect = now;
    fireActive = true;
  } else if (now - fireLastDetect > LATCH_TIME) {
    fireActive = false;
  }

  // 2. Rain Sensor (Analog) - Fast Trigger, Slow Release
  sensors_data.rain_raw = analogRead(RAIN_PIN);
  static int rainStableCount = 0;

  if (sensors_data.rain_raw < RAIN_THRESHOLD) {
    rainStableCount++;
    if (rainStableCount >= 3) { // Must be stable for 3 polls (~300ms)
      rainLastDetect = now;
      rainActive = true;
    }
  } else {
    rainStableCount = 0;
    if (now - rainLastDetect > LATCH_TIME) {
      rainActive = false;
    }
  }

  // 3. MPU6050 (Seismic) - Fast Trigger, Slow Release
  if (mpuFound) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);
    if (Wire.available() >= 6) {
      int16_t ax = (Wire.read() << 8) | Wire.read();
      int16_t ay = (Wire.read() << 8) | Wire.read();
      int16_t az = (Wire.read() << 8) | Wire.read();
      sensors_data.ax = ax / 16384.0 * 9.81;
      sensors_data.ay = ay / 16384.0 * 9.81;
      sensors_data.az = az / 16384.0 * 9.81;
      float d = sqrt(pow(sensors_data.ax - baseX, 2) +
                     pow(sensors_data.ay - baseY, 2) +
                     pow(sensors_data.az - baseZ, 2));

      if (d > SEISMIC_THRESHOLD) {
        seismicLastDetect = now;
        seismicActive = true;
      } else if (now - seismicLastDetect > LATCH_TIME) {
        seismicActive = false;
      }
    }
  }
}

void sendTelemetry() {
  DynamicJsonDocument doc(512);
  doc["device_id"] = deviceName;
  doc["fire_active"] = fireActive;
  doc["rain_active"] = rainActive;
  doc["seismic_active"] = seismicActive;
  doc["fire_raw"] = digitalRead(FIRE_PIN);
  doc["rain_raw"] = sensors_data.rain_raw;
  doc["ax"] = sensors_data.ax;
  doc["ay"] = sensors_data.ay;
  doc["az"] = sensors_data.az;
  doc["gx"] = 0;
  doc["gy"] = 0;
  doc["gz"] = 0;

  // 1. Serial Output (Legacy Support)
  serializeJson(doc, Serial);
  Serial.println();

  // 2. HTTP Output (Long Distance Tunneling)
  if (!isAPMode && WiFi.status() == WL_CONNECTED && serverBase.length() > 0) {
    static unsigned long lastHttpSend = 0;
    if (millis() - lastHttpSend > 500) { // Limit network noise
      lastHttpSend = millis();

      HTTPClient http;
      String url = serverBase;
      if (!url.startsWith("http"))
        url = "http://" + url;
      if (url.endsWith("/"))
        url = url.substring(0, url.length() - 1);
      url += "/api/telemetry";

      if (url.startsWith("https")) {
        WiFiClientSecure *client = new WiFiClientSecure;
        client->setInsecure();
        http.begin(*client, url);
      } else {
        http.begin(url);
      }

      http.setConnectTimeout(2000);
      http.addHeader("Content-Type", "application/json");

      String payload;
      serializeJson(doc, payload);
      int httpCode = http.POST(payload);
      if (httpCode > 0) {
        Serial.printf("INFO:Telemetry Cloud OK (%d)\n", httpCode);
      } else {
        Serial.printf("FAIL:Telemetry Cloud Error (%s)\n",
                      http.errorToString(httpCode).c_str());
      }
      http.end();
    }
  }
}

/* ================= LED LOGIC ================= */
void updateLEDs() {
  if (serverOverride)
    return;

  clearAll();

  if (seismicActive) {
    setGroup(b1_all, 8, strip.Color(255, 0, 0));
    setGroup(b2_path, 2,
             strip.Color(255, 0, 0)); // Building 2 segments turn RED
    setGroup(b2_fire_mark, 2, strip.Color(255, 0, 0));
    setGroup(evac1, 3, strip.Color(0, 255, 0)); // All paths turn GREEN
    setGroup(evac2, 3, strip.Color(0, 255, 0));
    digitalWrite(PIN_BUZZER, HIGH);
  } else if (fireActive) {
    blinkBuilding1();
    setGroup(b2_path, 2,
             strip.Color(0, 255, 0)); // 15, 16 stay GREEN (Safe Path)
    setGroup(b2_fire_mark, 2,
             strip.Color(255, 0, 0));           // 17, 18 turn RED (Hazard)
    setGroup(evac1, 3, strip.Color(0, 255, 0)); // EVAC1 Safe
    setGroup(evac2, 3,
             strip.Color(255, 0, 0)); // EVAC2 turns RED (Hazard proximity)
    digitalWrite(PIN_BUZZER, blinkState ? HIGH : LOW);
  } else if (rainActive) {
    setGroup(b1_all, 8, strip.Color(0, 100, 0));
    setGroup(b2_path, 2, strip.Color(0, 100, 0));
    setGroup(b2_fire_mark, 2, strip.Color(0, 100, 0));
    setGroup(evac1, 3, strip.Color(255, 0, 0));
    setGroup(evac2, 3, strip.Color(255, 0, 0));
    digitalWrite(PIN_BUZZER, LOW);
  } else {
    setGroup(b1_all, 8, strip.Color(0, 20, 0)); // Dim safe glow
    digitalWrite(PIN_BUZZER, LOW);
  }

  strip.setPixelColor(0, strip.Color(0, 100, 0)); // Health indicator
  strip.show();
}

/* ================= SETUP ================= */
void setup() {
  Serial.begin(115200);
  pinMode(FIRE_PIN, INPUT_PULLUP);
  pinMode(RAIN_PIN, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  strip.begin();
  strip.setBrightness(100);
  strip.show();

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission();

  // Calibration
  for (int i = 0; i < 50; i++) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);
    if (Wire.available() >= 6) {
      baseX += (int16_t(Wire.read() << 8) | Wire.read()) / 16384.0 * 9.81;
      baseY += (int16_t(Wire.read() << 8) | Wire.read()) / 16384.0 * 9.81;
      baseZ += (int16_t(Wire.read() << 8) | Wire.read()) / 16384.0 * 9.81;
    }
    delay(20);
  }
  baseX /= 50;
  baseY /= 50;
  baseZ /= 50;

  // --- WiFi & Network Setup ---
  macAddress = WiFi.macAddress();
  macAddress.replace(":", "");
  loadConfig();

  if (isConfigured && savedSSID.length() > 0) {
    WiFi.mode(WIFI_STA);
    if (savedPassword.length() == 0) {
      WiFi.begin(savedSSID.c_str()); // Open WiFi
    } else {
      WiFi.begin(savedSSID.c_str(), savedPassword.c_str());
    }
    Serial.print("INFO:Connecting to WiFi: ");
    Serial.println(savedSSID);

    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 20) {
      delay(500);
      Serial.print(".");
      retry++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      isAPMode = false;
      Serial.println("\nINFO:Connected! IP: " + WiFi.localIP().toString());

      // Start UDP listener for server discovery broadcasts
      udp.begin(DISCOVERY_PORT);
    } else {
      Serial.println("\nFAIL:WiFi failed. Entering AP mode.");
      isAPMode = true;
    }
  }

  if (isAPMode) {
    WiFi.mode(WIFI_AP);
    String apName =
        AP_SSID_PREFIX + macAddress.substring(macAddress.length() - 4);
    WiFi.softAP(apName.c_str());
    dnsServer.start(53, "*", WiFi.softAPIP());
    Serial.println("INFO:AP Start: " + apName);
  }

  server.on("/status", HTTP_GET, handleStatus);
  server.on("/status", HTTP_OPTIONS, handleStatus);
  server.on("/config", HTTP_POST, handleConfigure);
  server.on("/config", HTTP_OPTIONS, handleConfigure);
  server.on("/reset", HTTP_POST, []() {
    preferences.begin("hazard", false);
    preferences.clear();
    preferences.end();
    server.send(200, "text/plain", "Reset OK");
    delay(500);
    ESP.restart();
  });
  server.begin();

  Serial.println("INFO:System Booted");
}

void loop() {
  if (isAPMode)
    dnsServer.processNextRequest();
  server.handleClient();

  // 1. Command handling
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd.startsWith("SET_SAFE"))
      serverOverride = false;
    else if (cmd.startsWith("EVACUATE"))
      fireActive = true;
  }

  // 2. Sensor Polling
  unsigned long now = millis();
  if (now - lastPollTime >= POLLING_INTERVAL) {
    lastPollTime = now;
    readSensors();
    sendTelemetry();
  }

  // 2.5 Server Discovery (auto-update serverBase)
  if (!isAPMode && now - lastDiscoveryCheck >= DISCOVERY_CHECK_INTERVAL) {
    lastDiscoveryCheck = now;
    checkServerDiscovery();
  }

  // 3. LED updates (Smooth animation)
  updateLEDs();
}