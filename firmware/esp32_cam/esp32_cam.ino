#include "FS.h"
#include "SD_MMC.h"
#include "esp_camera.h"
#include "soc/rtc_cntl_reg.h" // Disable brownout problems
#include "soc/soc.h"          // Disable brownout problems
#include <ArduinoJson.h>
#include <DNSServer.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// ============================================================================
// AI-THINKER ESP32-CAM PIN DEFINITIONS
// ============================================================================
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#define LED_FLASH_PIN 4

// ============================================================================
// CONFIGURATION
// ============================================================================
#define AP_SSID_PREFIX "HAZARD_CAM_"
#define DNS_PORT 53
#define HTTP_PORT 80
#define STREAM_PORT 81
#define DISCOVERY_PORT 8002 // Match backend discovery port

#define POLLING_INTERVAL 1000 // 1Hz telemetry
#define BLINK_TIME 500

// ============================================================================
// GLOBAL STATE
// ============================================================================
WebServer configServer(HTTP_PORT);
WebServer streamServer(STREAM_PORT);
DNSServer dnsServer;
Preferences preferences;

// Mode flags
bool isAPMode = true;
bool isConfigured = false;
bool cameraReady = false;
bool sdReady = false;

// Saved configuration
String savedSSID = "";
String savedPassword = "";
String serverIP = "";
String deviceName = "";

// Runtime state
bool serverOverride = false;
bool alertActive = false;
int currentAlert = 0;

unsigned long lastPollTime = 0;
unsigned long blinkTimer = 0;
bool blinkState = false;
String macAddress = "";

// ============================================================================
// HTML TEMPLATES
// ============================================================================
const char *setupPageHTML = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HAZARD CAM Setup</title>
  <style>
    * { box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
    body { 
      margin: 0; padding: 20px; 
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      min-height: 100vh; color: #fff;
    }
    .container { max-width: 400px; margin: 0 auto; }
    h1 { text-align: center; color: #00d4ff; margin-bottom: 30px; }
    .card {
      background: rgba(255,255,255,0.1); border-radius: 16px;
      padding: 24px; backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.2);
    }
    .preview { 
      width: 100%; border-radius: 12px; margin-bottom: 20px;
      background: #000; aspect-ratio: 4/3; object-fit: cover;
    }
    label { display: block; margin: 16px 0 8px; color: #aaa; font-size: 14px; }
    input, select {
      width: 100%; padding: 14px; border: none; border-radius: 8px;
      background: rgba(255,255,255,0.15); color: #fff; font-size: 16px;
    }
    input:focus { outline: 2px solid #00d4ff; }
    button {
      width: 100%; padding: 16px; margin-top: 24px;
      background: linear-gradient(135deg, #00d4ff, #0099cc);
      border: none; border-radius: 8px; color: #fff;
      font-size: 18px; font-weight: bold; cursor: pointer;
      transition: transform 0.2s;
    }
    button:hover { transform: scale(1.02); }
    .status { text-align: center; color: #4ade80; margin-top: 16px; }
    .loader { display: none; text-align: center; margin-top: 20px; }
    .loader.active { display: block; }
    .scan-btn {
      background: rgba(255,255,255,0.2); margin-top: 10px; padding: 10px;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🎥 HAZARD CAM Setup</h1>
    <div class="card">
      <img id="preview" class="preview" src="/capture" alt="Camera Preview">
      
      <form id="configForm">
        <label>Camera Name</label>
        <input type="text" name="name" id="name" placeholder="e.g. Front Door" required>
        
        <label>WiFi Network</label>
        <input type="text" name="ssid" id="ssid" placeholder="Your WiFi SSID" required>
        
        <label>WiFi Password</label>
        <input type="password" name="password" id="password" placeholder="WiFi Password">
        
        <label>Server IP (Backend)</label>
        <input type="text" name="server" id="server" placeholder="e.g. 192.168.1.100:8000" required>
        
        <button type="submit">Connect & Register</button>
      </form>
      
      <div class="loader" id="loader">
        <p>Connecting to WiFi...</p>
      </div>
      <div class="status" id="status"></div>
    </div>
  </div>
  
  <script>
    // Refresh preview every 2 seconds
    setInterval(() => {
      document.getElementById('preview').src = '/capture?' + Date.now();
    }, 2000);
    
    document.getElementById('configForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const loader = document.getElementById('loader');
      const status = document.getElementById('status');
      
      loader.classList.add('active');
      status.textContent = '';
      
      const data = {
        name: form.name.value,
        ssid: form.ssid.value,
        password: form.password.value,
        server: form.server.value
      };
      
      try {
        const res = await fetch('/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if (result.status === 'ok') {
          status.textContent = '✓ ' + result.message;
          status.style.color = '#4ade80';
          setTimeout(() => {
            status.textContent = 'Rebooting... Connect to your network to access the camera.';
          }, 2000);
        } else {
          status.textContent = '✗ ' + result.message;
          status.style.color = '#f87171';
        }
      } catch (err) {
        status.textContent = '✗ Connection failed';
        status.style.color = '#f87171';
      }
      
      loader.classList.remove('active');
    });
  </script>
</body>
</html>
)rawliteral";

const char *successPageHTML = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Camera Active</title>
  <style>
    body { font-family: Arial; background: #1a1a2e; color: #fff; text-align: center; padding: 50px; }
    h1 { color: #4ade80; }
    .stream { max-width: 100%; border-radius: 12px; }
    .info { margin-top: 20px; color: #aaa; }
  </style>
</head>
<body>
  <h1>✓ Camera Connected</h1>
  <img class="stream" src="/stream" alt="Live Stream">
  <p class="info">Stream URL: <code>http://%IP%:81/stream</code></p>
</body>
</html>
)rawliteral";

// ============================================================================
// CAMERA INITIALIZATION
// ============================================================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA; // 640x480
  config.jpeg_quality = 12;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  return (err == ESP_OK);
}

// ============================================================================
// HELPERS
// ============================================================================
void logToSD(String msg) {
  String timestamp = "[" + String(millis() / 1000) + "s] ";
  String line = timestamp + msg;
  Serial.println(line);

  if (sdReady) {
    File file = SD_MMC.open("/hazard_logs.txt", FILE_APPEND);
    if (file) {
      file.println(line);
      file.close();
    }
  }
}

bool initSD() {
  // Use 1-bit mode to avoid conflict with Flash LED (GPIO 4)
  if (!SD_MMC.begin("/sdcard", true)) {
    Serial.println("INFO:SD Card Mount Failed");
    return false;
  }

  uint8_t cardType = SD_MMC.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("INFO:No SD card attached");
    return false;
  }

  Serial.println("INFO:SD Card Initialized");
  return true;
}

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

// ============================================================================
// HTTP HANDLERS - SETUP MODE
// ============================================================================
void handleSetupPage() {
  configServer.sendHeader("Access-Control-Allow-Origin", "*");
  configServer.send(200, "text/html", setupPageHTML);
}

void handleCapture() {
  configServer.sendHeader("Access-Control-Allow-Origin", "*");
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    configServer.send(500, "text/plain", "Camera capture failed");
    return;
  }
  configServer.sendHeader("Content-Disposition",
                          "inline; filename=capture.jpg");
  configServer.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleConfigure() {
  configServer.sendHeader("Access-Control-Allow-Origin", "*");
  configServer.sendHeader("Access-Control-Allow-Methods", "POST,GET,OPTIONS");
  configServer.sendHeader("Access-Control-Allow-Headers", "Content-Type");

  if (configServer.method() == HTTP_OPTIONS) {
    configServer.send(204);
    return;
  }

  if (!configServer.hasArg("plain")) {
    configServer.send(400, "application/json",
                      "{\"status\":\"error\",\"message\":\"No data\"}");
    return;
  }

  String body = configServer.arg("plain");
  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    configServer.send(400, "application/json",
                      "{\"status\":\"error\",\"message\":\"Invalid JSON\"}");
    return;
  }

  deviceName = doc["name"] | "Nexora_Cam";
  savedSSID = doc["ssid"] | "";
  savedPassword = doc["password"] | "";
  serverIP = doc["server_ip"] | "";

  if (savedSSID.length() == 0) {
    configServer.send(400, "application/json",
                      "{\"status\":\"error\",\"message\":\"Missing SSID\"}");
    return;
  }

  // Test WiFi connection
  WiFi.mode(WIFI_STA);
  if (savedPassword.length() == 0) {
    WiFi.begin(savedSSID.c_str());
  } else {
    WiFi.begin(savedSSID.c_str(), savedPassword.c_str());
  }

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    retry++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    logToSD("WIFI:Fail. Reverting to AP.");
    WiFi.mode(WIFI_AP);
    WiFi.softAP((AP_SSID_PREFIX + macAddress.substring(6)).c_str());
    configServer.send(
        200, "application/json",
        "{\"status\":\"error\",\"message\":\"WiFi connection failed\"}");
    return;
  }

  // Save to flash
  preferences.begin("hazard", false);
  preferences.putString("ssid", savedSSID);
  preferences.putString("pass", savedPassword);
  preferences.putString("server", serverIP);
  preferences.putString("name", deviceName);
  preferences.putBool("configured", true);
  preferences.end();

  // Register with backend server
  String response = "{\"status\":\"ok\",\"message\":\"Connected to " +
                    savedSSID + ". Registering with server...\"}";
  configServer.send(200, "application/json", response);

  delay(1000);

  // Attempt backend registration
  if (serverIP.length() > 0) {
    HTTPClient http;
    String url = serverIP;
    if (!url.startsWith("http"))
      url = "http://" + url;
    if (url.endsWith("/"))
      url = url.substring(0, url.length() - 1);
    url += "/api/cameras/register";

    if (url.startsWith("https")) {
      WiFiClientSecure *client = new WiFiClientSecure;
      client->setInsecure();
      http.begin(*client, url);
    } else {
      http.begin(url);
    }

    http.setConnectTimeout(3000);
    http.addHeader("Content-Type", "application/json");

    DynamicJsonDocument doc(256);
    doc["device_id"] = deviceName;
    doc["ip"] = WiFi.localIP().toString();
    doc["vflip"] = false;
    doc["hflip"] = false;

    String payload;
    serializeJson(doc, payload);

    int httpCode = http.POST(payload);
    if (httpCode > 0) {
      logToSD("REG:Backend result: " + String(httpCode));
    } else {
      logToSD("REG:Backend error: " +
              String(http.errorToString(httpCode).c_str()));
    }
    http.end();
  }

  delay(1000);
  ESP.restart();
}

void handleStatus() {
  configServer.sendHeader("Access-Control-Allow-Origin", "*");
  String json = "{";
  json += "\"type\":\"esp32_cam\",";
  json += "\"name\":\"" + deviceName + "\",";
  json += "\"camera\":" + String(cameraReady ? "true" : "false") + ",";
  json += "\"configured\":" + String(isConfigured ? "true" : "false") + ",";
  json += "\"mode\":\"" + String(isAPMode ? "ap" : "client") + "\",";
  json += "\"ip\":\"" +
          (isAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) +
          "\",";
  if (!isAPMode)
    json += "\"rssi\":" + String(WiFi.RSSI()) + ",";
  json += "\"uptime\":" + String(millis() / 1000) + ",";
  json += "\"stream_url\":\"http://" +
          (isAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) +
          ":81/stream\"";
  json += "}";
  configServer.send(200, "application/json", json);
}

void handleLogs() {
  configServer.sendHeader("Access-Control-Allow-Origin", "*");
  if (!sdReady) {
    configServer.send(503, "text/plain", "SD Card not available");
    return;
  }
  File file = SD_MMC.open("/hazard_logs.txt", FILE_READ);
  if (!file) {
    configServer.send(200, "text/plain", "Log file empty or not found.");
    return;
  }
  configServer.streamFile(file, "text/plain");
  file.close();
}

void handleDeleteLogs() {
  configServer.sendHeader("Access-Control-Allow-Origin", "*");
  if (SD_MMC.remove("/hazard_logs.txt")) {
    configServer.send(200, "text/plain", "Logs deleted");
  } else {
    configServer.send(500, "text/plain", "Failed to delete logs");
  }
}

void handleReset() {
  preferences.begin("hazard", false);
  preferences.clear();
  preferences.end();
  configServer.send(
      200, "application/json",
      "{\"status\":\"ok\",\"message\":\"Factory reset. Rebooting...\"}");
  delay(1000);
  ESP.restart();
}

// ============================================================================
// STREAM HANDLER (Port 81)
// ============================================================================
void handleStream() {
  WiFiClient client = streamServer.client();
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  streamServer.sendContent(response);

  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb)
      continue;

    String header = "--frame\r\n";
    header += "Content-Type: image/jpeg\r\n";
    header += "Content-Length: " + String(fb->len) + "\r\n\r\n";
    streamServer.sendContent(header);
    client.write(fb->buf, fb->len);
    streamServer.sendContent("\r\n");

    esp_camera_fb_return(fb);

    // Flash LED during alert
    if (alertActive && blinkState) {
      digitalWrite(LED_FLASH_PIN, HIGH);
      delay(30);
      digitalWrite(LED_FLASH_PIN, LOW);
    }

    delay(1);
  }
}

void handleStreamCapture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    streamServer.send(500, "text/plain", "Capture failed");
    return;
  }
  streamServer.sendHeader("Content-Disposition", "inline; filename=frame.jpg");
  streamServer.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

// ============================================================================
// DISCOVERY (UDP) - Send & Receive
// ============================================================================
WiFiUDP udp;
unsigned long lastDiscoveryCheck = 0;
#define DISCOVERY_CHECK_INTERVAL 2000 // Check every 2 seconds

void broadcastDiscovery() {
  if (isAPMode)
    return; // Only broadcast when connected to WiFi

  String msg = "{";
  msg += "\"type\":\"camera_discovery\",";
  msg += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  msg += "\"id\":\"" + deviceName + "\",";
  msg += "\"stream\":\"http://" + WiFi.localIP().toString() + ":81/stream\"";
  msg += "}";

  udp.beginPacket("255.255.255.255", DISCOVERY_PORT);
  udp.print(msg);
  udp.endPacket();
}

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
        if (newServer.length() > 0 && newServer != serverIP) {
          Serial.println("DISCOVERY:Server updated to: " + newServer);
          serverIP = newServer;

          // Save to preferences
          preferences.begin("hazard", false);
          preferences.putString("server", serverIP);
          preferences.end();
        }
      }
    }
  }
}

// ============================================================================
// TELEMETRY & COMMANDS
// ============================================================================
void sendTelemetry() {
  Serial.print("TELE:CAM:");
  Serial.print(deviceName);
  Serial.print(":");
  Serial.print(WiFi.localIP().toString());
  Serial.print(":");
  Serial.println(alertActive ? "ALERT" : "SAFE");
}

void updateStatusLED() {
  unsigned long interval = isAPMode ? 200 : 500;

  if (millis() - blinkTimer > interval) {
    blinkTimer = millis();
    blinkState = !blinkState;
  }

  if (isAPMode) {
    digitalWrite(LED_FLASH_PIN, blinkState);
  } else if (alertActive) {
    digitalWrite(LED_FLASH_PIN, blinkState);
  } else {
    digitalWrite(LED_FLASH_PIN, LOW);
  }
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector

  Serial.begin(115200);
  Serial.println("\n\n=== HAZARD CAM STARTING ===");

  pinMode(LED_FLASH_PIN, OUTPUT);
  digitalWrite(LED_FLASH_PIN, LOW);

  // Initialize SD Card early
  sdReady = initSD();
  logToSD("SYSTEM:Booted");

  // Get MAC address for unique AP name
  macAddress = WiFi.macAddress();
  macAddress.replace(":", "");

  // Initialize camera
  cameraReady = initCamera();
  if (!cameraReady) {
    Serial.println("INFO:Camera Init FAILED");
  } else {
    Serial.println("INFO:Camera Init OK");
  }

  // Load saved configuration
  preferences.begin("hazard", true);
  savedSSID = preferences.getString("ssid", "");
  savedPassword = preferences.getString("pass", "");
  serverIP = preferences.getString("server", "");
  deviceName = preferences.getString("name", "ESP32_CAM");
  isConfigured = preferences.getBool("configured", false);
  preferences.end();

  if (isConfigured && savedSSID.length() > 0) {
    // Try to connect to saved WiFi
    Serial.println("INFO:Connecting to saved WiFi: " + savedSSID);
    Serial.println("DEBUG:Password length: " + String(savedPassword.length()));
    Serial.println("DEBUG:Server: " + serverIP);
    WiFi.mode(WIFI_STA);
    WiFi.begin(savedSSID.c_str(), savedPassword.c_str());

    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 20) {
      delay(500);
      Serial.print(".");
      retry++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      isAPMode = false;
      logToSD("WIFI:Connected IP: " + WiFi.localIP().toString());

      // Start UDP for discovery
      udp.begin(DISCOVERY_PORT);
    } else {
      Serial.println("\nINFO:WiFi failed, starting AP mode");
      isConfigured = false;
    }
  }

  if (!isConfigured || isAPMode) {
    // Start AP mode for setup
    isAPMode = true;
    String apName = AP_SSID_PREFIX + macAddress.substring(6);
    WiFi.mode(WIFI_AP);
    WiFi.softAP(apName.c_str()); // Open network, no password

    // Start DNS server for captive portal
    dnsServer.start(DNS_PORT, "*", WiFi.softAPIP());

    Serial.println("INFO:AP Mode Started");
    Serial.println("INFO:SSID: " + apName);
    Serial.println("INFO:IP: " + WiFi.softAPIP().toString());
  }

  // Start config server (port 80)
  configServer.on("/", HTTP_GET, handleSetupPage);
  configServer.on("/capture", HTTP_GET, handleCapture);
  configServer.on("/config", HTTP_POST, handleConfigure);
  configServer.on("/config", HTTP_OPTIONS, handleConfigure); // Handle preflight
  configServer.on("/status", HTTP_GET, handleStatus);
  configServer.on("/status", HTTP_OPTIONS, handleStatus);
  configServer.on("/logs", HTTP_GET, handleLogs);
  configServer.on("/logs/delete", HTTP_POST, handleDeleteLogs);
  configServer.on("/reset", HTTP_POST, handleReset);
  configServer.onNotFound(handleSetupPage); // Captive portal redirect
  configServer.begin();

  // Start stream server (port 81)
  streamServer.on("/stream", HTTP_GET, handleStream);
  streamServer.on("/capture", HTTP_GET, handleStreamCapture);
  streamServer.on("/", HTTP_GET, []() {
    String html = successPageHTML;
    html.replace("%IP%", isAPMode ? WiFi.softAPIP().toString()
                                  : WiFi.localIP().toString());
    streamServer.send(200, "text/html", html);
  });
  streamServer.begin();

  Serial.println("INFO:System Booted");
  Serial.println("INFO:Config: http://" + (isAPMode
                                               ? WiFi.softAPIP().toString()
                                               : WiFi.localIP().toString()));
  Serial.println(
      "INFO:Stream: http://" +
      (isAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) +
      ":81/stream");
}

// ============================================================================
// LOOP
// ============================================================================
void loop() {
  // Handle DNS for captive portal (AP mode only)
  if (isAPMode) {
    dnsServer.processNextRequest();
  }

  // Handle HTTP requests
  configServer.handleClient();
  streamServer.handleClient();

  // Periodic tasks
  unsigned long now = millis();
  if (now - lastPollTime >= POLLING_INTERVAL) {
    lastPollTime = now;
    sendTelemetry();

    // Broadcast discovery every 5 seconds when connected
    if (!isAPMode && (now / 1000) % 5 == 0) {
      broadcastDiscovery();
    }
  }

  // Check for server discovery broadcasts
  if (!isAPMode && now - lastDiscoveryCheck >= DISCOVERY_CHECK_INTERVAL) {
    lastDiscoveryCheck = now;
    checkServerDiscovery();
  }

  // Serial command handling
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd.startsWith("SET_SAFE")) {
      alertActive = false;
      currentAlert = 0;
    } else if (cmd.startsWith("SET_ALERT:")) {
      currentAlert = cmd.substring(10).toInt();
      alertActive = (currentAlert > 0);
    } else if (cmd.startsWith("FLASH_ON")) {
      digitalWrite(LED_FLASH_PIN, HIGH);
    } else if (cmd.startsWith("FLASH_OFF")) {
      digitalWrite(LED_FLASH_PIN, LOW);
    } else if (cmd.startsWith("RESET")) {
      preferences.begin("hazard", false);
      preferences.clear();
      preferences.end();
      ESP.restart();
    }
  }

  // Status LED
  updateStatusLED();

  delay(1);
}
