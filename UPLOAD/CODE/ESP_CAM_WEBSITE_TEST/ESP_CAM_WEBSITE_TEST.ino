/*
 * MOD-EVAC-MS ESP32-CAM Firmware with WiFi Config Portal
 * 
 * FEATURES:
 * 1. First Boot: Hosts own WiFi hotspot "MOD-EVAC-CAM-XXXX"
 * 2. Connect to hotspot, visit 192.168.4.1 to configure:
 *    - WiFi SSID/Password
 *    - Camera Name
 *    - Backend Server URL
 * 3. Saves config to EEPROM/Preferences
 * 4. Reboots and connects to configured WiFi
 * 5. Streams MJPEG to /stream endpoint
 * 
 * RESET CONFIG: Hold BOOT button for 5 seconds on startup
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <HTTPClient.h>
#include "esp_http_server.h"

// ==========================================
// AI-CAM Pin Definition (ESP32-CAM AI-Thinker)
// ==========================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Flash LED Pin
#define LED_GPIO_NUM       4
#define BOOT_BUTTON_PIN    0

// ==========================================
// CAMERA SETTINGS
// ==========================================
#define VERTICAL_FLIP    true
#define HORIZONTAL_FLIP  false

// ==========================================
// GLOBALS
// ==========================================
Preferences prefs;
WebServer configServer(80);
httpd_handle_t stream_httpd = NULL;

String wifi_ssid = "";
String wifi_pass = "";
String cam_name = "CAM-01";
String backend_url = "";

bool configMode = false;

// ==========================================
// EEPROM FUNCTIONS
// ==========================================
void loadConfig() {
    prefs.begin("modevac", true); // Read-only
    wifi_ssid = prefs.getString("ssid", "");
    wifi_pass = prefs.getString("pass", "");
    cam_name = prefs.getString("name", "CAM-01");
    backend_url = prefs.getString("backend", "");
    prefs.end();
}

void saveConfig() {
    prefs.begin("modevac", false); // Write mode
    prefs.putString("ssid", wifi_ssid);
    prefs.putString("pass", wifi_pass);
    prefs.putString("name", cam_name);
    prefs.putString("backend", backend_url);
    prefs.end();
}

void clearConfig() {
    prefs.begin("modevac", false);
    prefs.clear();
    prefs.end();
}

// ==========================================
// CONFIG PORTAL HTML
// ==========================================
String getConfigHTML() {
    return R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MOD-EVAC Camera Setup</title>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { background: #1a1a2e; color: #eee; padding: 20px; margin: 0; }
        h1 { color: #00d26a; text-align: center; }
        .card { background: #16213e; border-radius: 12px; padding: 20px; max-width: 400px; margin: 20px auto; }
        label { display: block; margin: 15px 0 5px; color: #888; }
        input { width: 100%; padding: 12px; border: 1px solid #333; border-radius: 6px; background: #0f0f23; color: #fff; }
        button { width: 100%; padding: 14px; background: #00d26a; border: none; border-radius: 6px; color: #000; font-weight: bold; cursor: pointer; margin-top: 20px; }
        button:hover { background: #00b359; }
        .status { text-align: center; color: #888; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🎥 MOD-EVAC Camera</h1>
    <div class="card">
        <form action="/save" method="POST">
            <label>WiFi Network (SSID)</label>
            <input type="text" name="ssid" placeholder="Your WiFi Name" required>
            
            <label>WiFi Password</label>
            <input type="password" name="pass" placeholder="WiFi Password" required>
            
            <label>Camera Name</label>
            <input type="text" name="name" value="CAM-01" placeholder="CAM-01">
            
            <label>Backend Server URL (optional)</label>
            <input type="text" name="backend" placeholder="http://192.168.1.100:8000">
            
            <button type="submit">Save & Connect</button>
        </form>
    </div>
    <div class="status">Connect to your WiFi after saving. Camera will reboot.</div>
</body>
</html>
)rawliteral";
}

// ==========================================
// CONFIG SERVER HANDLERS
// ==========================================
void handleConfigRoot() {
    configServer.send(200, "text/html", getConfigHTML());
}

void handleConfigSave() {
    wifi_ssid = configServer.arg("ssid");
    wifi_pass = configServer.arg("pass");
    cam_name = configServer.arg("name");
    backend_url = configServer.arg("backend");
    
    saveConfig();
    
    configServer.send(200, "text/html", 
        "<html><body style='background:#1a1a2e;color:#eee;text-align:center;padding:50px;font-family:Arial;'>"
        "<h1 style='color:#00d26a;'>✓ Saved!</h1>"
        "<p>Camera will now connect to: <b>" + wifi_ssid + "</b></p>"
        "<p>Rebooting in 3 seconds...</p>"
        "</body></html>");
    
    delay(3000);
    ESP.restart();
}

void startConfigPortal() {
    configMode = true;
    
    // Generate unique AP name
    String apName = "MOD-EVAC-CAM-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    apName.toUpperCase();
    
    WiFi.mode(WIFI_AP);
    WiFi.softAP(apName.c_str(), "modevac123"); // Password: modevac123
    
    Serial.println("\n=== CONFIG MODE ===");
    Serial.println("WiFi Hotspot: " + apName);
    Serial.println("Password: modevac123");
    Serial.println("Config URL: http://192.168.4.1");
    
    configServer.on("/", handleConfigRoot);
    configServer.on("/save", HTTP_POST, handleConfigSave);
    configServer.begin();
    
    // Blink LED to indicate config mode
    pinMode(LED_GPIO_NUM, OUTPUT);
}

// ==========================================
// MJPEG STREAM HANDLER
// ==========================================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    char part_buf[64];

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;
    
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            res = ESP_FAIL;
            break;
        }

        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }
        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, 64, _STREAM_PART, fb->len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
        }

        esp_camera_fb_return(fb);
        if (res != ESP_OK) break;
    }
    return res;
}

esp_err_t capture_handler(httpd_req_t *req) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return ESP_OK;
}

esp_err_t status_handler(httpd_req_t *req) {
    char json[256];
    snprintf(json, sizeof(json),
        "{\"name\":\"%s\",\"ip\":\"%s\",\"stream\":\"/stream\",\"status\":\"online\"}",
        cam_name.c_str(), WiFi.localIP().toString().c_str());
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, json, strlen(json));
    return ESP_OK;
}

void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 81;

    httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler };
    httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = capture_handler };
    httpd_uri_t status_uri = { .uri = "/status", .method = HTTP_GET, .handler = status_handler };

    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        httpd_register_uri_handler(stream_httpd, &capture_uri);
        httpd_register_uri_handler(stream_httpd, &status_uri);
    }
}

// ==========================================
// CAMERA INIT
// ==========================================
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
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed: 0x%x\n", err);
        return false;
    }

    // Apply flip
    sensor_t *s = esp_camera_sensor_get();
    if (s) {
        s->set_vflip(s, VERTICAL_FLIP ? 1 : 0);
        s->set_hmirror(s, HORIZONTAL_FLIP ? 1 : 0);
    }
    
    return true;
}

// ==========================================
// BACKEND REGISTRATION
// ==========================================
void registerWithBackend() {
    if (backend_url.length() == 0) return;

    HTTPClient http;
    String url = backend_url + "/api/cameras/register";
    
    Serial.println("[HTTP] Registering with backend: " + url);
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    
    // Create unique ID based on MAC
    String deviceId = "ESP-CAM-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    deviceId.toUpperCase();

    String json = "{\"device_id\":\"" + deviceId + "\", \"ip\":\"" + WiFi.localIP().toString() + "\", \"vflip\":" + (VERTICAL_FLIP ? "true" : "false") + "}";
    
    int httpResponseCode = http.POST(json);
    
    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("[HTTP] Response: " + String(httpResponseCode));
        Serial.println(response);
    } else {
        Serial.print("[HTTP] Error code: ");
        Serial.println(httpResponseCode);
    }
    
    http.end();
}

// ==========================================
// SETUP
// ==========================================
void setup() {
    Serial.begin(115200);
    Serial.println("\n\n=== MOD-EVAC-MS ESP32-CAM ===");
    
    pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
    
    // Check if BOOT button held = reset config
    if (digitalRead(BOOT_BUTTON_PIN) == LOW) {
        Serial.println("BOOT button held - clearing config...");
        clearConfig();
        delay(2000);
    }
    
    // Load saved config
    loadConfig();
    
    // If no WiFi configured, start config portal
    if (wifi_ssid.length() == 0) {
        Serial.println("No WiFi configured - starting config portal...");
        if (!initCamera()) {
            Serial.println("Camera init failed!");
        }
        startConfigPortal();
        return;
    }
    
    // Try to connect to saved WiFi
    Serial.println("Connecting to: " + wifi_ssid);
    WiFi.mode(WIFI_STA);
    WiFi.begin(wifi_ssid.c_str(), wifi_pass.c_str());
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\nWiFi connection failed! Starting config portal...");
        startConfigPortal();
        return;
    }
    
    Serial.println("\n[OK] WiFi Connected!");
    Serial.print("Camera Name: "); Serial.println(cam_name);
    Serial.print("Camera IP: "); Serial.println(WiFi.localIP());
    Serial.println("Stream: http://" + WiFi.localIP().toString() + ":81/stream");
    
    // Init camera
    if (!initCamera()) {
        Serial.println("Camera init failed!");
        return;
    }
    Serial.println("[OK] Camera Ready");
    
    // Start stream server
    startCameraServer();
    Serial.println("[OK] Stream Server Started on port 81");
    
    // Auto-register with backend (if configured)
    if (backend_url.length() > 0) {
        registerWithBackend();
    }
}

// ==========================================
// LOOP
// ==========================================
void loop() {
    if (configMode) {
        configServer.handleClient();
        
        // Blink LED in config mode
        static unsigned long lastBlink = 0;
        if (millis() - lastBlink > 500) {
            lastBlink = millis();
            digitalWrite(LED_GPIO_NUM, !digitalRead(LED_GPIO_NUM));
        }
    }
    delay(10);
}
