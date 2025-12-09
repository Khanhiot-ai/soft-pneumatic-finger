#include <AccelStepper.h>
#include <TMCStepper.h>

// --- C?U HÌNH CHÂN (KHÔNG Ð?I) ---
#define X_STEP_PIN      54
#define X_DIR_PIN       55
#define X_ENABLE_PIN    38
#define E0_STEP_PIN     26
#define E0_DIR_PIN      28
#define E0_ENABLE_PIN   24
#define E1_STEP_PIN     36
#define E1_DIR_PIN      34
#define E1_ENABLE_PIN   30
#define SERIAL_PORT_X   Serial2
#define R_SENSE         0.11f

// --- KH?I T?O Ð?I TU?NG (KHÔNG Ð?I) ---
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
TMC2209Stepper driverX(&SERIAL_PORT_X, R_SENSE, 0b00);
AccelStepper stepperE0(AccelStepper::DRIVER, E0_STEP_PIN, E0_DIR_PIN);
AccelStepper stepperE1(AccelStepper::DRIVER, E1_STEP_PIN, E1_DIR_PIN);

// --- CÁC H?NG S? T?C Ð? (KHÔNG Ð?I) ---
const float ACCEL_X = 5000.0;
const float DEFAULT_CLAMP_SPEED = 2000.0;
const float ACCEL_MAIN_DRIVE = 1000.0;
const float DEFAULT_SPEED_MAIN_DRIVE = 1000.0;

bool pid_mode = false;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  SERIAL_PORT_X.begin(115200);

  // --- SETUP MOTOR (KHÔNG Ð?I) ---
  pinMode(X_ENABLE_PIN, OUTPUT);
  pinMode(E0_ENABLE_PIN, OUTPUT);
  pinMode(E1_ENABLE_PIN, OUTPUT);
  digitalWrite(X_ENABLE_PIN, LOW);
  digitalWrite(E0_ENABLE_PIN, HIGH);
  digitalWrite(E1_ENABLE_PIN, HIGH);
  
  driverX.begin();
  driverX.toff(5);
  driverX.rms_current(800);
  driverX.microsteps(16);

  stepperX.setAcceleration(ACCEL_X);
  stepperX.setMaxSpeed(4000); 
  stepperE0.setAcceleration(ACCEL_MAIN_DRIVE);
  stepperE0.setMaxSpeed(DEFAULT_SPEED_MAIN_DRIVE);
  stepperE1.setAcceleration(ACCEL_MAIN_DRIVE);
  stepperE1.setMaxSpeed(DEFAULT_SPEED_MAIN_DRIVE);

  Serial.println("MKS Ready. Awaiting commands.");
}

void loop() {
  handleSerialFromPC();
  handleSerialFromUno();
  
  stepperE0.run();
  stepperE1.run();

  if (pid_mode) {
    stepperX.runSpeed();
  } else {
    stepperX.run();
  }
}

void handleSerialFromUno() {
  if (Serial1.available() > 0) {
    String msg = Serial1.readStringUntil('\n');
    msg.trim();
    if (msg.startsWith("pid_speed:")) {
      if (pid_mode) {
        float speed_from_uno = msg.substring(10).toFloat();
        // THAY Ð?I 1: Ð?o ngu?c t?c d? t? Uno
        stepperX.setSpeed(-speed_from_uno); 
      }
    } else if (msg.startsWith("DATA:")) {
      Serial.println(msg.substring(5)); 
    }
  }
}

void handleSerialFromPC() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    processCommand(cmd);
  }
}

void processCommand(String cmd_str) {
  String action = "";
  long steps_val = 0;
  float speed_val = 0;

  int firstColon = cmd_str.indexOf(':');
  if (firstColon == -1) { 
    action = cmd_str; 
  } else {
    action = cmd_str.substring(0, firstColon);
    String params = cmd_str.substring(firstColon + 1);
    int secondColon = params.indexOf(':');
    if (secondColon != -1) {
      steps_val = params.substring(0, secondColon).toInt();
      speed_val = params.substring(secondColon + 1).toFloat();
    } else {
      steps_val = params.toInt();
    }
  }
  action.toLowerCase();
  
  if (action == "up") { 
    float speed = (speed_val > 0) ? speed_val : DEFAULT_SPEED_MAIN_DRIVE;
    stepperE0.setMaxSpeed(speed);
    stepperE1.setMaxSpeed(speed);
    stepperE0.move(steps_val); 
    stepperE1.move(steps_val); 
  } 
  else if (action == "down") { 
    float speed = (speed_val > 0) ? speed_val : DEFAULT_SPEED_MAIN_DRIVE;
    stepperE0.setMaxSpeed(speed);
    stepperE1.setMaxSpeed(speed);
    stepperE0.move(-steps_val); 
    stepperE1.move(-steps_val); 
  } 
  else if (action == "clamp") {
    Serial.println("CMD: Starting PID clamp mode (Reversed).");
    pid_mode = true;
    Serial1.println("start_pid");
    // THAY Ð?I 2: Ð?o ngu?c t?c d? k?p ban d?u
    stepperX.setSpeed(-DEFAULT_CLAMP_SPEED);
  } else if (action == "release") {
    Serial.println("CMD: Releasing clamp (Reversed).");
    pid_mode = false;
    Serial1.println("stop_pid");
    stepperX.stop();
    stepperX.setCurrentPosition(0);
    // THAY Ð?I 3: Ð?o ngu?c hu?ng di chuy?n khi nh?
    stepperX.moveTo(steps_val);
  } 
  else if (action == "setpoint") {
    Serial.println("CMD: Forwarding new setpoint to Uno.");
    Serial1.println(cmd_str);
  }
  else if (action == "e") { 
    digitalWrite(E0_ENABLE_PIN, LOW); 
    digitalWrite(E1_ENABLE_PIN, LOW);
    Serial.println("INFO: Up/Down motors ENABLED.");
  }
  else if (action == "x") { 
    digitalWrite(E0_ENABLE_PIN, HIGH); 
    digitalWrite(E1_ENABLE_PIN, HIGH);
    Serial.println("INFO: Up/Down motors DISABLED.");
  }
}
