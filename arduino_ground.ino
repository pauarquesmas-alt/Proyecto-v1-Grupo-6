// RECEPTOR SIMPLE (PC <-> Receptor <-> Emisor)
// - Reenvía todo lo que llega del Emisor al PC
// - 'Fallo' -> LED sensor ON
// - >5s sin datos -> LED link ON
// - Comando 'P' desde PC -> parpadeo LED 13

#include <SoftwareSerial.h>

#define BAUDRATE         9600
#define LED_P_PIN        13    // Parpadeo por 'P'
#define LED_SENSOR_PIN    7    // Alarma sensor (Fallo)
#define LED_LINK_PIN      8    // Alarma enlace (timeout)
#define LINK_TIMEOUT_MS 5000
#define BLINK_MS         100

SoftwareSerial EmisorSerial(10, 11); // RX=10 (desde TX emisor), TX=11 (opcional)

unsigned long lastRx = 0;
bool linkDown = false;

bool blinking = false;
unsigned long blinkStart = 0;

// Buffer muy simple para detectar líneas y buscar "Fallo"
char buf[32];
uint8_t blen = 0;

void resetBuf() {
  blen = 0;
  buf[0] = '\0';
}

void setup() {
  Serial.begin(BAUDRATE);       // PC
  EmisorSerial.begin(BAUDRATE); // Emisor

  pinMode(LED_P_PIN, OUTPUT);
  pinMode(LED_SENSOR_PIN, OUTPUT);
  pinMode(LED_LINK_PIN, OUTPUT);
  digitalWrite(LED_P_PIN, LOW);
  digitalWrite(LED_SENSOR_PIN, LOW);
  digitalWrite(LED_LINK_PIN, LOW);

  resetBuf();
  lastRx = millis();
}

void loop() {
  // ---- Datos desde EMISOR ----
  while (EmisorSerial.available()) {
    char c = EmisorSerial.read();
    Serial.write(c);                 // Puente a PC
    lastRx = millis();               // Marca recepción
    if (linkDown) {                  // Si estaba caído, recupera
      linkDown = false;
      digitalWrite(LED_LINK_PIN, LOW);
      Serial.println("INFO:LINK_UP");
    }

    // Construcción de línea sencilla
    if (c == '\n' || c == '\r') {
      if (blen > 0) {
        buf[blen] = '\0';
        // ¿contiene "Fallo"?
        if (strstr(buf, "Fallo")) {
          digitalWrite(LED_SENSOR_PIN, HIGH);
          Serial.println("ALARM:SENSOR_FAIL");
        } else {
          // Si llegan datos normales, apaga alarma de sensor
          digitalWrite(LED_SENSOR_PIN, LOW);
        }
        resetBuf();
      }
    } else if (blen < sizeof(buf) - 1) {
      buf[blen++] = c;
    } else {
      resetBuf(); // Evita desbordes
    }
  }

  // ---- Comandos desde PC ----
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'P') {
      blinking = true;
      blinkStart = millis();
      digitalWrite(LED_P_PIN, HIGH);
    }
  }

  // ---- Parpadeo corto ----
  if (blinking && (millis() - blinkStart >= BLINK_MS)) {
    digitalWrite(LED_P_PIN, LOW);
    blinking = false;
  }

  // ---- Timeout de enlace ----
  if (!linkDown && (millis() - lastRx >= LINK_TIMEOUT_MS)) {
    linkDown = true;
    digitalWrite(LED_LINK_PIN, HIGH);
    Serial.println("ALARM:LINK_DOWN");
  }
}

