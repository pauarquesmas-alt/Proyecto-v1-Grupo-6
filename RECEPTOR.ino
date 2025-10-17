#include <SoftwareSerial.h>

#define LED_PIN 13                 
#define LED_ALARMA_SENSOR 6        // S'encén si el satèl·lit envia "Fallo"
#define LED_ALARMA_COMS 7          // S'encén si portem >5s sense rebre res
#define BLINK_DURATION_MS 100
#define BAUDRATE 9600

// Enllaç amb el satèl·lit (Arduino satel·lit)
SoftwareSerial EmisorSerial(10, 11); // RX=10 (rep del sat), TX=11 (envia al sat)

int isBlinking = 0;
unsigned long lastBlinkTime = 0;

// Temporitzador de comunicació
unsigned long lastRxMillis = 0;
const unsigned long TIMEOUT_COMS_MS = 5000;


String rxLine;

void setup() {
  Serial.begin(BAUDRATE);        // PC
  EmisorSerial.begin(BAUDRATE);  // Satèl·lit

  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_ALARMA_SENSOR, OUTPUT);
  pinMode(LED_ALARMA_COMS, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_ALARMA_SENSOR, LOW);
  digitalWrite(LED_ALARMA_COMS, LOW);

  delay(500);
  lastRxMillis = millis();       
  Serial.println("READY");       
}

void loop() {
  
  while (EmisorSerial.available()) {
    char c = EmisorSerial.read();

    
    Serial.write(c);

    
    lastRxMillis = millis();
    digitalWrite(LED_ALARMA_COMS, LOW);  // Comunicació OK ara mateix

   
    if (c == '\n') {
      rxLine.trim();

      if (rxLine.length() > 0) {
        if (rxLine.equalsIgnoreCase("Fallo")) {
          // Alarma de sensor des del satèl·lit
          digitalWrite(LED_ALARMA_SENSOR, HIGH);
          // Avís textual a la GUI/PC
          Serial.println("ALARM_SENSOR_ON");
        } else if (rxLine.startsWith("T:")) {
          // Lectura correcta: apaguem alarma de sensor
          digitalWrite(LED_ALARMA_SENSOR, LOW);
          // (Opcional) indicar a la GUI que tot OK
          Serial.println("ALARM_SENSOR_OFF");
        }
      }

      rxLine = "";
    } else {
      rxLine += c;
    }
  }

  // --- Comandes des de PC (p. ex. Python) ---
  while (Serial.available()) {
    char command = Serial.read();
    if (command == 'P') {
      isBlinking = 1;
      lastBlinkTime = millis();
      digitalWrite(LED_PIN, HIGH);
      Serial.println("ACK P");   // Confirmació visible a Python
    }
  }

Temporització del parpelleig del LED 13
  if (isBlinking && (millis() - lastBlinkTime) >= BLINK_DURATION_MS) {
    digitalWrite(LED_PIN, LOW);
    isBlinking = 0;
  }

  // --- Alarma de comunicació (si no rebem res en >5s) ---
  if ((millis() - lastRxMillis) > TIMEOUT_COMS_MS) {
    // Si ja està encès, deixar-lo encès; si estava apagat, encendre'l
    if (digitalRead(LED_ALARMA_COMS) == LOW) {
      digitalWrite(LED_ALARMA_COMS, HIGH);
      Serial.println("ALARM_COMMS_ON");
    }
  }
}

