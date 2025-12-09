#include <AccelStepper.h>
#include <TMCStepper.h>

// --- CÁC CHÂN CHO CÁC CH?C NANG (MKS Gen L v1.0) ---
// Tr?c X (di?u khi?n riêng)
#define X_STEP_PIN      54  // Chân STEP cho tr?c X
#define X_DIR_PIN       55  // Chân DIR cho tr?c X
#define X_ENABLE_PIN    38  // Chân ENABLE cho tr?c X

// Tr?c E0 và E1 (di?u khi?n chung)
#define E0_STEP_PIN     26  // Chân STEP cho tr?c E0
#define E0_DIR_PIN      28  // Chân DIR cho tr?c E0
#define E0_ENABLE_PIN   24  // Chân ENABLE cho tr?c E0
#define E1_STEP_PIN     36  // Chân STEP cho tr?c E1
#define E1_DIR_PIN      34  // Chân DIR cho tr?c E1
#define E1_ENABLE_PIN   30  // Chân ENABLE cho tr?c E1

// --- C?u hình cho Driver TMC UART ---
#define SERIAL_PORT_X   Serial2 // C?ng Serial ph?n c?ng cho driver X trên MKS Gen L
#define R_SENSE         0.11f   // Giá tr? di?n tr? c?m bi?n dòng, thu?ng là 0.11

// =========================================================================
// === THAY Ð?I GIÁ TR? NÀY Ð? DÒ TÌM NGU?NG K?P ===
// B?t d?u v?i giá tr? th?p (ví d?: 10) và tang d?n n?u nó không d?ng.
// N?u nó d?ng quá s?m, hãy gi?m giá tr? này.
#define STALL_VALUE_X   200
// =========================================================================

// --- KH?I T?O Ð?NG CO VÀ DRIVER ---
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
TMC2209Stepper driverX(&SERIAL_PORT_X, R_SENSE, 0b00);

AccelStepper stepperE0(AccelStepper::DRIVER, E0_STEP_PIN, E0_DIR_PIN);
AccelStepper stepperE1(AccelStepper::DRIVER, E1_STEP_PIN, E1_DIR_PIN);

// --- CÁC THAM S? M?C Ð?NH ---
const float ACCEL_X = 1200.0;
const float DEFAULT_SPEED_X = 1600.0;
const float ACCEL_MAIN_DRIVE = 1000.0;
const float DEFAULT_SPEED_MAIN_DRIVE = 1000.0;

void setup() {
  Serial.begin(9600);
  SERIAL_PORT_X.begin(115200);

  // Logic Handshake
  while (!Serial.available()) {
    delay(100); 
  }
  if (Serial.read() == '1') {
    Serial.println("INIT:MKS Gen L v1.0 (UART) - Handshake OK - Ready");
  }

  // C?u hình các chân ENABLE
  pinMode(X_ENABLE_PIN, OUTPUT);
  pinMode(E0_ENABLE_PIN, OUTPUT);
  pinMode(E1_ENABLE_PIN, OUTPUT);
  
  // B?t driver X d? giao ti?p UART, vô hi?u hóa các driver còn l?i
  digitalWrite(X_ENABLE_PIN, LOW); // LOW = B?t. Ph?i b?t d? giao ti?p UART
  digitalWrite(E0_ENABLE_PIN, HIGH);
  digitalWrite(E1_ENABLE_PIN, HIGH);

  // C?u hình driver TMC qua UART
  driverX.begin();
  driverX.toff(5);
  driverX.rms_current(800);   // Ð?t dòng di?n (mA) phù h?p v?i d?ng co c?a b?n
  driverX.microsteps(16);
  driverX.TCOOLTHRS(0xFFFFF); // T?t CoolStep d? StallGuard ?n d?nh
  driverX.semin(5);
  driverX.semax(2);
  driverX.sedn(0b01);
  driverX.SGTHRS(STALL_VALUE_X); // Ð?t ngu?ng StallGuard

  // Cài d?t thông s? cho AccelStepper X
  stepperX.setAcceleration(ACCEL_X);
  stepperX.setMaxSpeed(DEFAULT_SPEED_X);

  // Cài d?t thông s? cho c?p E0, E1
  stepperE0.setAcceleration(ACCEL_MAIN_DRIVE);
  stepperE0.setMaxSpeed(DEFAULT_SPEED_MAIN_DRIVE);
  stepperE1.setAcceleration(ACCEL_MAIN_DRIVE);
  stepperE1.setMaxSpeed(DEFAULT_SPEED_MAIN_DRIVE);

  delay(2000); 
  Serial.println("Arduino Ready. Waiting for commands...");
  Serial.print("Current STALL_VALUE_X is set to: ");
  Serial.println(STALL_VALUE_X);
}

// --- HÀM DI CHUY?N K?P ÐÃ S?A Ð?I Ð? IN RA GIÁ TR? DÒ TÌM ---
void moveXUntilStall(int direction, float speed) {
  Serial.println("INFO: Starting clamp sequence... Watch SG_RESULT values below.");
  stepperX.setMaxSpeed(speed);
  stepperX.setAcceleration(ACCEL_X);
  stepperX.move(999999L * direction); // Ð?t m?c tiêu di chuy?n r?t xa

  while (stepperX.distanceToGo() != 0) {
    stepperX.run();
    // Ð?c và in giá tr? StallGuard t? driver
    uint16_t sg_result = driverX.SG_RESULT();
    
    Serial.print("SG_RESULT = ");
    Serial.println(sg_result);

    // Khi sg_result gi?m xu?ng b?ng ho?c th?p hon ngu?ng -> dã va ch?m
    if (sg_result <= STALL_VALUE_X) { 
        stepperX.stop(); // D?ng d?ng co
        stepperX.runToPosition(); // Hoàn thành vi?c d?ng
        
        Serial.print("INFO: Stall Detected! Triggered with SG_RESULT = ");
        Serial.println(sg_result);
        Serial.println("DONE: Clamp Complete"); // G?i tín hi?u hoàn thành
        return; // Thoát kh?i hàm
    }
    delay(50); // Ð?i m?t chút d? d? d?c trên Serial Monitor
  }
}

void loop() {
  // G?i run() cho các d?ng co
  stepperE0.run();
  stepperE1.run();
  stepperX.run();

  // Ki?m tra d? li?u t? Serial
  if (Serial.available() > 0) {
    String cmd_str = Serial.readStringUntil('\n');
    cmd_str.trim();

    if (cmd_str.length() > 0) {
      Serial.print("ACK:");
      Serial.println(cmd_str);
      processCommand(cmd_str);
    }
  }

  // Logic g?i tín hi?u "DONE" cho các l?nh không d?ng b?
  static bool lastRunningState = false;
  bool currentRunningState = stepperX.isRunning() || stepperE0.isRunning() || stepperE1.isRunning();
  if (lastRunningState && !currentRunningState) {
    // Ch? in "Motion Complete" n?u không ph?i là l?nh k?p, vì l?nh k?p dã có tín hi?u "DONE" riêng.
    // Ði?u này tránh vi?c in ra 2 l?n DONE.
  }
  lastRunningState = currentRunningState;
}

void processCommand(String cmd_str) {
  String action = "";
  long steps_val = 0;
  float speed_val = 0;

  // Phân tích cú pháp l?nh (không thay d?i)
  int firstColon = cmd_str.indexOf(':');
  if (firstColon == -1) {
    action = cmd_str; 
  } else {
    action = cmd_str.substring(0, firstColon);
    String params = cmd_str.substring(firstColon + 1);
    int secondColon = params.indexOf(':');
    if (secondColon != -1) {
      speed_val = params.substring(secondColon + 1).toFloat();
      steps_val = params.substring(0, secondColon).toInt();
    } else {
      steps_val = params.toInt();
    }
  }
  action.toLowerCase();

  float xSpeed = (speed_val > 0) ? speed_val : DEFAULT_SPEED_X;
  float mainDriveSpeed = (speed_val > 0) ? speed_val : DEFAULT_SPEED_MAIN_DRIVE;

  // --- L?NH CHO CO C?U CHUNG E0, E1 ---
  if (action == "u") { // Ch?y t?i
    stepperE0.setMaxSpeed(mainDriveSpeed);
    stepperE1.setMaxSpeed(mainDriveSpeed);
    stepperE0.move(steps_val);
    stepperE1.move(steps_val);
  } else if (action == "d") { // Ch?y lùi
    stepperE0.setMaxSpeed(mainDriveSpeed);
    stepperE1.setMaxSpeed(mainDriveSpeed);
    stepperE0.move(-steps_val); 
    stepperE1.move(-steps_val);
  
  // --- L?NH CHO TR?C X RIÊNG BI?T ---
  } else if (action == "l") { // "Left" - Di chuy?n X sang trái
    stepperX.setMaxSpeed(xSpeed);
    stepperX.move(-steps_val);
  } else if (action == "r") { // "Right" - Di chuy?n X sang ph?i
    stepperX.setMaxSpeed(xSpeed);
    stepperX.move(steps_val);

  // --- L?nh k?p s? d?ng StallGuard ---
  } else if (action == "c") { // "Clamp" - K?p vào
    // Gi? s? chi?u duong (1) là chi?u k?p
    moveXUntilStall(1, xSpeed);

  // --- L?NH CHUNG ---
  } else if (action == "e") { // Enable các d?ng co ph?
    digitalWrite(E0_ENABLE_PIN, LOW);
    digitalWrite(E1_ENABLE_PIN, LOW);
    Serial.println("INFO:E0/E1 Motors Enabled");
  } else if (action == "x") { // Disable các d?ng co ph?
    digitalWrite(E0_ENABLE_PIN, HIGH);
    digitalWrite(E1_ENABLE_PIN, HIGH);
    Serial.println("INFO:E0/E1 Motors Disabled");
  } else if (action == "stop") { // D?ng kh?n c?p
    stepperX.stop();
    stepperE0.stop();
    stepperE1.stop();
    Serial.println("INFO:STOP ALL Initiated");
  } else {
    Serial.println("INFO:Unknown command received.");
  }
}
