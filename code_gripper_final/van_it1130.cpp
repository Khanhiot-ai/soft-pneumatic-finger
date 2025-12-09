#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <PID_v1.h>

// =================================================================
// =========== C?u hình và tham s? h? th?ng =========================
// =================================================================
const float MAX_PRESSURE_KPA = 500.0f;
const long  SERIAL_BAUD_RATE = 115200;

// Ð?nh nghia ch? d? di?u khi?n
enum ControlMode { MODE_PID, MODE_MANUAL };

// =================================================================
// =========== Class di?u khi?n van (VanController) =================
// =================================================================
class VanController {
public:
    // Constructor
    VanController(uint8_t i2c_addr, uint8_t monitor_pin, const char* name)
        : dac(), i2cAddress(i2c_addr), monitorPin(monitor_pin), vanName(name),
          pressure_kPa(0.0f), zeroVoltage(0.0f), emaVoltage(0.0f),
          currentMode(MODE_PID), // M?c d?nh là ch? d? PID
          manualPercentage(0),
          pid(&pidInput_kPa, &pidOutput_dac, &pidSetpoint_kPa, Kp, Ki, Kd, DIRECT) {}

    void begin() {
        dac.begin(i2cAddress);
        pid.SetOutputLimits(0, 4095); // Gi?i h?n d?u ra PID kh?p v?i DAC
        pid.SetMode(AUTOMATIC);      // B?t PID
    }

    // Ð?t ch? d? di?u khi?n
    void setMode(ControlMode mode) {
        currentMode = mode;
        if (currentMode == MODE_PID) {
            pid.SetMode(AUTOMATIC); // B?t PID khi ? ch? d? t? d?ng
        } else {
            pid.SetMode(MANUAL); // T?t PID khi ? ch? d? th? công
        }
    }
    
    // Ð?t ph?n tram th? công
    void setManualPercentage(int percentage) {
        manualPercentage = constrain(percentage, 0, 100);
    }
    
    // Ð?t áp su?t m?c tiêu (ch? cho ch? d? PID)
    void setSetpoint(float kpa) {
        pidSetpoint_kPa = constrain(kpa, 0.0f, MAX_PRESSURE_KPA);
    }

    void update() {
        // 1. Luôn d?c và tính toán áp su?t hi?n t?i
        long rawSum = 0;
        for (int i = 0; i < 20; i++) { rawSum += analogRead(monitorPin); }
        float avgVoltage = (rawSum / 20.0f) * (5.0f / 1023.0f);
        emaVoltage = (0.2f * avgVoltage) + (0.8f * emaVoltage);
        float voltageDifference = emaVoltage - zeroVoltage;
        if (fabs(voltageDifference) < 0.03f) {
            pressure_kPa = 0.0f;
        } else {
            float positiveVoltage = max(0.0f, voltageDifference);
            pressure_kPa = (positiveVoltage / (5.0f - zeroVoltage)) * MAX_PRESSURE_KPA;
            pressure_kPa = constrain(pressure_kPa, 0.0f, MAX_PRESSURE_KPA);
        }

        // 2. D?a vào ch? d? hi?n t?i d? quy?t d?nh hành d?ng
        if (currentMode == MODE_PID) {
            pidInput_kPa = pressure_kPa;
            pid.Compute();
            dac.setVoltage((uint16_t)pidOutput_dac, false);
        } else {
            uint16_t dacValue = map(manualPercentage, 0, 100, 0, 4095);
            dac.setVoltage(dacValue, false);
        }
    }

    void zeroCalibrate() {
        long sum = 0; for (int i = 0; i < 200; i++) { sum += analogRead(monitorPin); delay(2); }
        zeroVoltage = (sum / 200.0f) * (5.0 / 1023.0);
        emaVoltage = zeroVoltage;
        Serial.print(F("ZERO CAL [")); Serial.print(vanName); Serial.print(F("]: "));
        Serial.print(zeroVoltage, 3); Serial.println(F(" V"));
    }

    void setTunings(double p, double i, double d) { pid.SetTunings(p, i, d); }
    float getPressure() const { return pressure_kPa; }
    const char* getName() const { return vanName; }
    float getSetpoint() const { return pidSetpoint_kPa; }

private:
    Adafruit_MCP4725 dac;
    uint8_t i2cAddress, monitorPin;
    const char* vanName;
    float pressure_kPa, zeroVoltage, emaVoltage;
    ControlMode currentMode;
    int manualPercentage;
    double Kp = 20.0, Ki = 5.0, Kd = 1.0;
    double pidSetpoint_kPa = 0.0, pidInput_kPa, pidOutput_dac;
    PID pid;
};

VanController van1(0x60, A0, "ITV1");
VanController van2(0x60, A1, "ITV2");

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    van1.begin(); van2.begin();
    Serial.println("\n=== ITV1030 Controller - Dual Mode (PID/Manual) ===");
    delay(1000);
    van1.zeroCalibrate(); van2.zeroCalibrate();
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        char cmdType = cmd.charAt(0);
        cmd.remove(0, 1); // B? ký t? d?u
        int van_idx = cmd.indexOf(',');
        int vanNum = cmd.substring(0, van_idx).toInt();
        cmd.remove(0, van_idx + 1);

        switch(cmdType) {
            case 'M': // Mode Change: M1,A
                if (vanNum == 1) van1.setMode(cmd.charAt(0) == 'A' ? MODE_PID : MODE_MANUAL);
                else van2.setMode(cmd.charAt(0) == 'A' ? MODE_PID : MODE_MANUAL);
                Serial.print("[OK] Van "); Serial.print(vanNum); Serial.println(cmd.charAt(0) == 'A' ? " -> Auto (PID)" : " -> Manual (%)");
                break;
            case 'P': // Manual Percentage: P1,75
                if (vanNum == 1) van1.setManualPercentage(cmd.toInt());
                else van2.setManualPercentage(cmd.toInt());
                Serial.print("[OK] Van "); Serial.print(vanNum); Serial.print(" -> Manual % set to: "); Serial.println(cmd);
                break;
            case 'S': // Setpoint: S1,250.5
                if (vanNum == 1) van1.setSetpoint(cmd.toFloat());
                else van2.setSetpoint(cmd.toFloat());
                Serial.print("[OK] Van "); Serial.print(vanNum); Serial.print(" -> Setpoint set to: "); Serial.println(cmd);
                break;
            case 'T': { // Tune: T1,20.0,5.0,1.0
                int ki_idx = cmd.indexOf(',');
                double p = cmd.substring(0, ki_idx).toFloat();
                cmd.remove(0, ki_idx + 1);
                int kd_idx = cmd.indexOf(',');
                double i = cmd.substring(0, kd_idx).toFloat();
                double d = cmd.substring(kd_idx + 1).toFloat();
                if (vanNum == 1) van1.setTunings(p,i,d); else van2.setTunings(p,i,d);
                Serial.print("[OK] Van "); Serial.print(vanNum); Serial.println(" -> PID Tunings Updated");
                break;
            }
            case 'Z': // Zero Calibrate
                van1.zeroCalibrate(); van2.zeroCalibrate();
                break;
        }
    }
    
    van1.update();
    van2.update();
    
    Serial.print(van1.getName()); Serial.print(F(":")); Serial.print(van1.getPressure(), 1);
    Serial.print('\t');
    Serial.print(van2.getName()); Serial.print(F(":")); Serial.println(van2.getPressure(), 1);

    delay(50);
}
