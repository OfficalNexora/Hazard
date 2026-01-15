#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <esp_now.h>

//  CAMERA MODEL 
#define CAMERA_MODEL_AI_THINKER

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


//  WIFI AP 
const char* ssid = "ESP32-CAM";
const char* password = "12345678";

WebServer server(80);

//  ESP-NOW 
typedef struct {
  int command;
} Message;

Message incoming;

//  FLASH 
#define FLASH_LED_PIN 4

//  HTML PAGE 
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>ESP32-CAM</title>
  <style>
    body { background:#111; color:#0f0; font-family:monospace; text-align:center; }
    button { font-size:20px; padding:10px 20px; margin:10px; }
    img { width:90%; border:2px solid #0f0; }
  </style>
</head>
<body>
  <h1>ESP32-CAM LIVE</h1>
  <img src="/stream">
  <br>
  <button onclick="fetch('/flash/on')">FLASH ON</button>
  <button onclick="fetch('/flash/off')">FLASH OFF</button>
</body>
</html>
)rawliteral";

//  STREAM HANDLER 
void handleStream() {
  WiFiClient client = server.client();
  String response =
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  client.print(response);

  while (client.connected()) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) continue;

    client.printf(
      "--frame\r\n"
      "Content-Type: image/jpeg\r\n"
      "Content-Length: %u\r\n\r\n",
      fb->len
    );
    client.write(fb->buf, fb->len);
    client.print("\r\n");

    esp_camera_fb_return(fb);
    delay(50);
  }
}

//  ESP-NOW RECEIVE 
void onReceive(const esp_now_recv_info *info, const uint8_t *data, int len) {
  memcpy(&incoming, data, sizeof(incoming));

  if (incoming.command == 1) {
    digitalWrite(FLASH_LED_PIN, HIGH);
  } 
  else if (incoming.command == 0) {
    digitalWrite(FLASH_LED_PIN, LOW);
  }
}

// =================== SETUP ===================
void setup() {
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  Serial.begin(115200);

  // CAMERA CONFIG
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
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_camera_init(&config);

  // WIFI AP
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(ssid, password);

  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());

  // ESP-NOW
  esp_now_init();
  esp_now_register_recv_cb(onReceive);

  // WEB ROUTES
  server.on("/", []() {
    server.send_P(200, "text/html", INDEX_HTML);
  });

  server.on("/stream", HTTP_GET, handleStream);

  server.on("/flash/on", []() {
    digitalWrite(FLASH_LED_PIN, HIGH);
    server.send(200, "text/plain", "ON");
  });

  server.on("/flash/off", []() {
    digitalWrite(FLASH_LED_PIN, LOW);
    server.send(200, "text/plain", "OFF");
  });

  server.begin();
}

// =================== LOOP ===================
void loop() {
  server.handleClient();
}
