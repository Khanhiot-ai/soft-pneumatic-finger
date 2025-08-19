// PSE573-01 (1–5V) + Bơm ON/OFF (không PWM, không PID)
// Dùng được cho relay (active-LOW/active-HIGH) hoặc MOSFET như công tắc số

// ----- Chân tín hiệu -----
const int PIN_PSE_AIN   = A0;   // Tín hiệu analog từ PSE573 (dây ĐEN)
const int PIN_PUMP_OUT  = 7;    // Điều khiển relay/MOSFET (ON/OFF)

// ----- Cấu hình phần cứng điều khiển bơm -----
const bool RELAY_ACTIVE_LOW = true; // true: mức LOW = bật (đa số module relay)
                                     // false: mức HIGH = bật (MOSFET hoặc relay active-HIGH)

// ----- Tham số cảm biến -----
const float VREF   = 5.0;     // Tham chiếu ADC (UNO/MEGA)
const int   ADCMAX = 1023;

// Điện áp tương ứng 0 kPa (dải -100..+100 kPa cho PSE573-01): lý thuyết ~3.00V.
// Đo thực tế lúc 0 kPa rồi chỉnh số này cho đúng.
float ZERO_V = 3.00;

// Bộ lọc EMA giảm nhiễu
const float EMA_ALPHA = 0.15;
float emaV = 3.0;

// ----- Setpoint & Hysteresis -----
float setpoint_kPa = 50.0;   // Mục tiêu (ví dụ 50 kPa). Có thể chỉnh qua Serial: SP=60
float band_kPa     = 2.0;    // Dải trễ ±2 kPa. Có thể chỉnh qua Serial: BAND=3

// ----- Chống nhấp nháy (bảo vệ bơm) -----
const unsigned long MIN_ON_MS  = 3000;  // tối thiểu bật 3s
const unsigned long MIN_OFF_MS = 3000;  // tối thiểu tắt 3s

// ----- Giới hạn an toàn -----
const float SAFE_MAX_KPA = 95.0;  // nếu vượt -> tắt bơm
const float SAFE_MIN_KPA = -95.0; // nếu dưới -> tắt bơm (tùy ứng dụng có thể bỏ)
const float SENSOR_MIN_V = 0.5;   // phát hiện hở mạch/ngắn mạch
const float SENSOR_MAX_V = 4.9;

// ====== Hàm tiện ích ======
float adcToVolt(int adc){ return adc * (VREF / ADCMAX); }
// Quy đổi 1..5V -> -100..+100 kPa (1V=-100 kPa, 3V=0 kPa, 5V=+100 kPa)
float voltToKpa(float v){ return (v - 3.0f) * 50.0f; }

void pumpWrite(bool on){
  if (RELAY_ACTIVE_LOW){
    digitalWrite(PIN_PUMP_OUT, on ? LOW : HIGH);
  } else {
    digitalWrite(PIN_PUMP_OUT, on ? HIGH : LOW);
  }
}

void printStatus(float vCorr, float p_kPa, bool pumpOn){
  Serial.print("V="); Serial.print(vCorr, 3);
  Serial.print("  P(kPa)="); Serial.print(p_kPa, 1);
  Serial.print("  SP="); Serial.print(setpoint_kPa, 1);
  Serial.print("  BAND=±"); Serial.print(band_kPa, 1);
  Serial.print("  PUMP="); Serial.println(pumpOn ? "ON" : "OFF");
}

void handleSerial(){
  if (!Serial.available()) return;
  String s = Serial.readStringUntil('\n'); s.trim();
  s.replace(",", "."); // cho phép dùng dấu phẩy
  if (s.startsWith("SP=")){
    setpoint_kPa = s.substring(3).toFloat();
    Serial.print("OK SP="); Serial.println(setpoint_kPa,1);
  } else if (s.startsWith("BAND=")){
    band_kPa = max(0.2f, s.substring(5).toFloat());
    Serial.print("OK BAND=±"); Serial.println(band_kPa,1);
  } else if (s.startsWith("ZERO=")){
    ZERO_V = s.substring(5).toFloat();
    Serial.print("OK ZERO_V="); Serial.println(ZERO_V,3);
  } else if (s.equalsIgnoreCase("STATUS") || s=="?"){
    // sẽ in ở vòng lặp
  } else {
    Serial.println("Cmd?  SP=xx  BAND=xx  ZERO=xx  STATUS");
  }
}

void setup(){
  pinMode(PIN_PUMP_OUT, OUTPUT);
  pumpWrite(false); // đảm bảo tắt lúc khởi động

  Serial.begin(115200);
  delay(300);
  Serial.println(F("PSE573 ON/OFF control (no PWM/PID). Commands: SP=60  BAND=3  ZERO=2.98  STATUS"));
}

void loop(){
  handleSerial();

  // Đọc & lọc điện áp
  int adc = analogRead(PIN_PSE_AIN);
  float v = adcToVolt(adc);
  emaV = EMA_ALPHA * v + (1 - EMA_ALPHA) * emaV;

  // Hiệu chỉnh zero (đưa 0 kPa về ~3.00V)
  float vCorr = emaV + (3.0 - ZERO_V);

  // Kiểm tra cảm biến lỗi
  static bool pumpOn = false;
  static unsigned long lastChange = 0;

  bool sensorFault = (vCorr < SENSOR_MIN_V) || (vCorr > SENSOR_MAX_V);

  // Tính áp suất
  float p_kPa = voltToKpa(vCorr);

  // Ngưỡng ON/OFF với hysteresis
  float onTh  = setpoint_kPa - band_kPa;
  float offTh = setpoint_kPa + band_kPa;

  // Chống nhấp nháy
  unsigned long now = millis();
  bool canToggle = pumpOn ? (now - lastChange >= MIN_ON_MS)
                          : (now - lastChange >= MIN_OFF_MS);

  // An toàn & điều khiển
  if (sensorFault || p_kPa > SAFE_MAX_KPA || p_kPa < SAFE_MIN_KPA){
    if (pumpOn){ pumpOn = false; pumpWrite(false); lastChange = now; }
  } else {
    if (!pumpOn && p_kPa < onTh && canToggle){
      pumpOn = true; pumpWrite(true); lastChange = now;
    } else if (pumpOn && p_kPa > offTh && canToggle){
      pumpOn = false; pumpWrite(false); lastChange = now;
    }
  }

  // In trạng thái mỗi 200 ms
  static unsigned long t0=0;
  if (now - t0 >= 200){
    t0 = now;
    printStatus(vCorr, p_kPa, pumpOn);
  }

  delay(100);
}
