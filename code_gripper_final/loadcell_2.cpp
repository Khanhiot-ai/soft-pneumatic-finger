#include <Wire.h>
#include <AS5600.h>
#include <HX711.h>

// =======================================================================
//                        CÀI Ð?T C?M BI?N
// =======================================================================

#pragma region "Cài d?t C?m bi?n và H?ng s?"
const int LOADCELL_DOUT_PIN_1 = 2;
const int LOADCELL_SCK_PIN_1 = 3;
const int LOADCELL_DOUT_PIN_2 = 4;
const int LOADCELL_SCK_PIN_2 = 5;
float calibration_factor_1 = -700.0;
float calibration_factor_2 = 740.0;
const float GRAVITY = 9.81;
#pragma endregion

#pragma region "Bi?n Toàn c?c và Ð?i tu?ng"
HX711 cell_1, cell_2;
AS5600 as5600;
volatile long revolution_count = 0;
volatile int last_raw_angle = 0;
long total_encoder_position = 0;
#pragma endregion


// =======================================================================
//                              CHUONG TRÌNH CHÍNH
// =======================================================================
void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  Serial.println("\n>>> Arduino Sensor Hub: Ready <<<");

  // Kh?i t?o Loadcell
  cell_1.begin(LOADCELL_DOUT_PIN_1, LOADCELL_SCK_PIN_1);
  cell_1.set_scale(calibration_factor_1);
  cell_1.tare();
  cell_2.begin(LOADCELL_DOUT_PIN_2, LOADCELL_SCK_PIN_2);
  cell_2.set_scale(calibration_factor_2);
  cell_2.tare();

  // Kh?i t?o Encoder AS5600
  if (as5600.isConnected()) {
    last_raw_angle = as5600.readAngle();
  } else {
    Serial.println("AS5600 not found! Halting.");
    while (1);
  }
  
  Serial.println("System Ready. Sending data...");
  Serial.println("---------------------------------");
}

void loop() {
  handleSerialCommands();

  // Ð?c c?m bi?n
  float force1_grams = cell_1.get_units(5);
  float force2_grams = cell_2.get_units(5);
  float force1_newtons = (force1_grams / 1000.0) * GRAVITY;
  float force2_newtons = (force2_grams / 1000.0) * GRAVITY;
  
  updateEncoderPosition();

  // In d? li?u ra Serial
  printData(force1_newtons, force2_newtons, total_encoder_position);
  
  delay(100);
}


// =======================================================================
//                            CÁC HÀM CH?C NANG
// =======================================================================

void handleSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "t") {
      cell_1.tare();
      Serial.println("--> Tare Scale 1 OK.");
    } else if (command == "u") {
      cell_2.tare();
      Serial.println("--> Tare Scale 2 OK.");
    } else if (command == "z") {
      noInterrupts();
      revolution_count = 0;
      last_raw_angle = as5600.readAngle(); // L?y m?c góc hi?n t?i d? tính toán ti?p
      total_encoder_position = last_raw_angle;
      interrupts();
      Serial.println("--> Encoder position zeroed.");
    }
  }
}

void updateEncoderPosition() {
  int current_raw_angle = as5600.readAngle();
  
  noInterrupts();
  int diff = current_raw_angle - last_raw_angle;
  if (diff > 2048) { revolution_count--; } 
  else if (diff < -2048) { revolution_count++; }
  total_encoder_position = (revolution_count * 4096) + current_raw_angle;
  last_raw_angle = current_raw_angle;
  interrupts();
}

void printData(float force1_n, float force2_n, long position_raw) {
  // Ð?nh d?ng: L?c1,L?c2,V?TríThô
  Serial.print(force1_n, 2);
  Serial.print(",");
  Serial.print(force2_n, 2);
  Serial.print(",");
  Serial.println(position_raw);
}
