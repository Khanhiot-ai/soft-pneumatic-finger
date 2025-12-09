#include <Adafruit_NeoPixel.h>

// --- CẤU HÌNH PHẦN CỨNG ---
#define PIN            6                 // Chân điều khiển NeoPixel
#define NUMPIXELS      8                 // Vòng tròn 8 bóng
#define LED_TYPE       (NEO_GRB + NEO_KHZ800)

// Tùy chọn: chân sync cho camera (có thể bỏ nếu không dùng)
#define SYNC_PIN       7

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, LED_TYPE);

// Các mode chiếu sáng
enum LightMode {
  MODE_OFF = 0,
  MODE_TOP,
  MODE_RIGHT,
  MODE_BOTTOM,
  MODE_LEFT,
  MODE_ALL_WHITE
};

LightMode currentMode = MODE_OFF;

// ---------- HÀM TIỆN ÍCH ----------

void allOff() {
  for (int i = 0; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, 0, 0, 0);
  }
  pixels.show();
}

// Bật một nhóm LED liên tiếp với màu (mặc định trắng)
void lightGroup(uint8_t start, uint8_t count,
                uint8_t r = 150, uint8_t g = 150, uint8_t b = 150) {
  allOff();
  for (uint8_t i = 0; i < count; i++) {
    uint8_t idx = (start + i) % NUMPIXELS;
    pixels.setPixelColor(idx, pixels.Color(r, g, b));
  }
  pixels.show();
}

// Mapping 8 LED quanh camera:
// 0-1: TOP, 2-3: RIGHT, 4-5: BOTTOM, 6-7: LEFT
void applyMode(LightMode mode) {
  // xung sync cho camera nếu cần
  digitalWrite(SYNC_PIN, HIGH);

  switch (mode) {
    case MODE_OFF:
      allOff();
      break;

    case MODE_TOP:
      lightGroup(0, 2);  // LED 0,1
      break;

    case MODE_RIGHT:
      lightGroup(2, 2);  // LED 2,3
      break;

    case MODE_BOTTOM:
      lightGroup(4, 2);  // LED 4,5
      break;

    case MODE_LEFT:
      lightGroup(6, 2);  // LED 6,7
      break;

    case MODE_ALL_WHITE:
      allOff();
      for (int i = 0; i < NUMPIXELS; i++) {
        pixels.setPixelColor(i, pixels.Color(255, 255, 255));
      }
      pixels.show();
      break;
  }

  delayMicroseconds(200);   // xung sync rất ngắn
  digitalWrite(SYNC_PIN, LOW);
}

void printHelp() {
  Serial.println(F("=== NeoPixel Photometric Stereo (8-LED ring) ==="));
  Serial.println(F("Commands:"));
  Serial.println(F("  't' -> TOP    (LED 0,1)"));
  Serial.println(F("  'r' -> RIGHT  (LED 2,3)"));
  Serial.println(F("  'b' -> BOTTOM (LED 4,5)"));
  Serial.println(F("  'l' -> LEFT   (LED 6,7)"));
  Serial.println(F("  'w' -> all white"));
  Serial.println(F("  '0' -> all off"));
  Serial.println(F("  'h' -> help"));
  Serial.println();
}

// ---------- SETUP & LOOP ----------

void setup() {
  Serial.begin(115200);

  pixels.begin();
  pixels.setBrightness(80);  // chỉnh tăng/giảm cho phù hợp camera
  pixels.show();

  pinMode(SYNC_PIN, OUTPUT);
  digitalWrite(SYNC_PIN, LOW);

  allOff();
  printHelp();
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case '0':
        currentMode = MODE_OFF;
        break;
      case 't':
      case 'T':
        currentMode = MODE_TOP;
        break;
      case 'r':
      case 'R':
        currentMode = MODE_RIGHT;
        break;
      case 'b':
      case 'B':
        currentMode = MODE_BOTTOM;
        break;
      case 'l':
      case 'L':
        currentMode = MODE_LEFT;
        break;
      case 'w':
      case 'W':
        currentMode = MODE_ALL_WHITE;
        break;
      case 'h':
      case 'H':
        printHelp();
        break;
      default:
        // ignore unknown
        break;
    }

    applyMode(currentMode);
  }
}
