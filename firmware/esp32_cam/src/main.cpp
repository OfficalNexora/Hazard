#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// ============================================================================
// AI-THINKER ESP32-CAM PIN DEFINITIONS
// ============================================================================
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
#define LED_FLASH_PIN      4

// ============================================================================
// GLOBAL STATE
// ============================================================================
WebServer server(81);
Preferences preferences;
bool isAPMode = false;
String ssid = "";
String password = "";
String server_ip = "";

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
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
    // I set the grab mode to 'LATEST' to discard old frames if the network is slow, minimizing latency.
    config.grab_mode = CAMERA_GRAB_LATEST;

    esp_err_t err = esp_camera_init(&config);
    return (err == ESP_OK);
}

// ============================================================================
// MJPEG HANDLER
// ============================================================================
void handleStream() {
    WiFiClient client = server.client();
    String response = "HTTP/1.1 200 OK\r\n";
    response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
    server.sendContent(response);

    while (client.connected()) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) continue;

        String header = "--frame\r\n";
        header += "Content-Type: image/jpeg\r\n";
        header += "Content-Length: " + String(fb->len) + "\r\n\r\n";
        server.sendContent(header);
        client.write(fb->buf, fb->len);
        server.sendContent("\r\n");

        esp_camera_fb_return(fb);
        delay(1);
    }
}

// ============================================================================
// PROVISIONING HANDLER
// ============================================================================
void handleConfig() {
    if (server.hasArg("plain")) {
        StaticJsonDocument<256> doc;
        deserializeJson(doc, server.arg("plain"));
        
        ssid = doc["ssid"].as<String>();
        password = doc["password"].as<String>();
        server_ip = doc["server_ip"].as<String>();

        preferences.begin("nexora", false);
        preferences.putString("ssid", ssid);
        preferences.putString("password", password);
        preferences.putString("server_ip", server_ip);
        preferences.end();

        server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Rebooting...\"}");
        delay(1000);
        ESP.restart();
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_FLASH_PIN, OUTPUT);
    digitalWrite(LED_FLASH_PIN, LOW);

    if (!initCamera()) {
        Serial.println("Camera Init Failed");
        return;
    }

    preferences.begin("nexora", true);
    ssid = preferences.getString("ssid", "");
    password = preferences.getString("password", "");
    server_ip = preferences.getString("server_ip", "");
    preferences.end();

    if (ssid == "") {
        isAPMode = true;
        String apName = "NEXORA_CAM_" + String((uint32_t)ESP.getEfuseMac(), HEX);
        WiFi.softAP(apName.c_str());
        Serial.println("AP Mode: " + apName);
        Serial.println("IP: " + WiFi.softAPIP().toString());
    } else {
        WiFi.begin(ssid.c_str(), password.c_str());
        int retry = 0;
        while (WiFi.status() != WL_CONNECTED && retry < 20) {
            delay(500);
            Serial.print(".");
            retry++;
        }
        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("\nWiFi Connected. IP: " + WiFi.localIP().toString());
        } else {
            Serial.println("\nWiFi Failed. Reverting to AP Mode.");
            isAPMode = true;
            WiFi.softAP("NEXORA_CAM_SETUP");
        }
    }

    server.on("/stream", HTTP_GET, handleStream);
    server.on("/config", HTTP_POST, handleConfig);
    server.begin();
}

void loop() {
    server.handleClient();
    delay(1);
}
