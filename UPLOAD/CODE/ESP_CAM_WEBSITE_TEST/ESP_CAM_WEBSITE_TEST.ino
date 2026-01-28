#include <Adafruit_NeoPixel.h>

#define PIN 5
#define NUM_LEDS 40

Adafruit_NeoPixel strip(NUM_LEDS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
  strip.show();
}

void loop() {
  strip.fill(strip.Color(255, 0, 0)); // ALL RED
  strip.show();
  delay(500);
}
