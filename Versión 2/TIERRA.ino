#include <SoftwareSerial.h>

#define LED_TX_PC 13
#define LED_ALARMA_SENSOR 6
#define LED_ALARMA_COMS 7
#define BLINK_DURATION_MS 100
#define BAUDRATE 9600

SoftwareSerial EmisorSerial(10, 11); // RX=10, TX=11

bool isBlinking = false;
unsigned long lastBlinkTime = 0;
unsigned long lastRxMillis = 0;
const unsigned long TIMEOUT_COMS_MS = 5000;

void setup() {
  Serial.begin(BAUDRATE);
  EmisorSerial.begin(BAUDRATE);

  pinMode(LED_TX_PC, OUTPUT);
  pinMode(LED_ALARMA_SENSOR, OUTPUT);
  pinMode(LED_ALARMA_COMS, OUTPUT);
  digitalWrite(LED_TX_PC, LOW);
  digitalWrite(LED_ALARMA_SENSOR, LOW);
  digitalWrite(LED_ALARMA_COMS, LOW);

  delay(500);
  lastRxMillis = millis();
  Serial.println("READY");
}

void loop() {

  // ===== SAT -> PC (LÍNEA COMPLETA) =====
  if (EmisorSerial.available()) {
    String linea = EmisorSerial.readStringUntil('\n');
    linea.trim();

    if (linea.length() > 0) {
      Serial.println(linea);    // reenviar la línea entera
      lastRxMillis = millis();
      digitalWrite(LED_ALARMA_COMS, LOW);
    }
  }

  // ===== PC -> SAT =====
  while (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    if (comando.length() > 0) {
      EmisorSerial.println(comando);
      digitalWrite(LED_TX_PC, HIGH);
      lastBlinkTime = millis();
      isBlinking = true;
    }
  }

  if (isBlinking && (millis() - lastBlinkTime >= BLINK_DURATION_MS)) {
    digitalWrite(LED_TX_PC, LOW);
    isBlinking = false;
  }

  // ===== Alarma comunicación =====
  if ((millis() - lastRxMillis) > TIMEOUT_COMS_MS) {
    if (digitalRead(LED_ALARMA_COMS) == LOW) {
      digitalWrite(LED_ALARMA_COMS, HIGH);
      Serial.println("ALARM_COMMS_ON");
    }
  }
}


