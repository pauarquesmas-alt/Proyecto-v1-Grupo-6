#include <SoftwareSerial.h>
#define LED_PIN 13
#define BLINK_DURATION_MS 100
#define BAUDRATE 9600
SoftwareSerial EmisorSerial(10, 11); // RX=10, TX=11

int isBlinking = 0;
unsigned long lastBlinkTime = 0;

void setup() {
  Serial.begin(BAUDRATE);
  EmisorSerial.begin(BAUDRATE);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  delay(500);
  Serial.println("READY");   // <-- línea de bienvenida para Python
}

void loop() {
  // Puente Emisor -> PC
  while (EmisorSerial.available()) {
    char c = EmisorSerial.read();
    Serial.write(c);         // reenvío transparente
  }

  // Comandos desde Python
  while (Serial.available()) {
    char command = Serial.read();
    if (command == 'P') {
      isBlinking = 1;
      lastBlinkTime = millis();
      digitalWrite(LED_PIN, HIGH);
      Serial.println("ACK P");  // <-- confirmación visible en Python
    }
  }

  // Temporización del parpadeo
  if (isBlinking && (millis() - lastBlinkTime) >= BLINK_DURATION_MS) {
    digitalWrite(LED_PIN, LOW);
    isBlinking = 0;
  }
}

