#include <SoftwareSerial.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ===== LCD I2C =====
LiquidCrystal_I2C lcd(0x3F, 16, 2);  // dirección 0x3F, 16x2

// leds para ver cosas del satelite
#define LED_RX_SAT        13      // se enciende si llega algo
#define LED_ALARMA_SENSOR 6       // alarma sensor
#define LED_ALARMA_COMS   7       // alarma cuando no hay coms

#define BAUDRATE          9600
#define TIMEOUT_COMS_MS   15000

// ===== BOTONERA ANALÓGICA A0 =====
const uint8_t PIN_KEYPAD = A0;
const int N_BUTTONS = 5;
const char LABELS[N_BUTTONS] = { 'A', 'B', 'C', 'D', 'E' };

const int PRESS_DELTA = 60;
const int TOLERANCE   = 30;

// VALORES DE TU CALIBRACIÓN
int baseline = 1023;                    // reposo
int refVal[N_BUTTONS] = { 0, 45, 90, 0, 0 };  // A,B,C,D,E (D/E sin usar)

// Identificador de grupo que llega desde el satélite
String GRUPO = "G6:";

SoftwareSerial EmisorSerial(10, 11); // serie secundario (10 RX, 11 TX)
unsigned long lastRxMillis = 0;
bool alarmaComsActiva = false;

// últimas lecturas recibidas
float ultimaTemp = 0.0;
float ultimaHum  = 0.0;

// ==== buffer para media de últimas 10 temperaturas ====
const int N_MEDIA = 10;
float ultimasT[N_MEDIA];
int idxT = 0;
int numT = 0;

float mediaUltimasT() {
  if (numT == 0) return 0.0;
  float suma = 0;
  for (int i = 0; i < numT; i++) suma += ultimasT[i];
  return suma / numT;
}

// ====== CHECKSUM =====
uint8_t calcularChecksum(const String &msg) {
  uint16_t suma = 0;
  for (char c : msg) suma += (uint8_t)c;
  return (uint8_t)(suma & 0xFF);
}

// manda el mensaje y le pone el checksum detras, añadiendo GRUPO
void enviarConChecksum(String msg) {
  String cuerpo = GRUPO + msg;
  uint8_t cs = calcularChecksum(cuerpo);
  EmisorSerial.print(cuerpo);
  EmisorSerial.print("*");
  EmisorSerial.println(cs);
}

// === Botonera: funciones de ayuda ===
int readAvg(int n = 10, int dlyMs = 2) {
  long sum = 0;
  for (int i = 0; i < n; i++) {
    sum += analogRead(PIN_KEYPAD);
    delay(dlyMs);
  }
  return (int)(sum / n);
}

int classifyButton(int adc) {
  int best = -1;
  int bestDiff = 9999;
  for (int i = 0; i < N_BUTTONS; i++) {
    int d = abs(adc - refVal[i]);
    if (d < bestDiff) {
      bestDiff = d;
      best = i;
    }
  }
  if (best != -1 && bestDiff <= TOLERANCE) return best;
  return -1;
}

// === Mostrar TEMPERATURA Y HUMEDAD en el LCD ===
void lcdMostrarTemperaturaHumedad(float t, float h) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(t, 1);
  lcd.print("C");
  lcd.setCursor(0, 1);
  lcd.print("H:");
  lcd.print(h, 1);
  lcd.print("%");
}

// Solo temperatura
void lcdMostrarSoloTemperatura(float t) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("TEMPERATURA");
  lcd.setCursor(0, 1);
  lcd.print(t, 1);
  lcd.print(" C");
}

// Solo humedad
void lcdMostrarSoloHumedad(float h) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("HUMEDAD");
  lcd.setCursor(0, 1);
  lcd.print(h, 1);
  lcd.print(" %");
}

// Media temperatura
void lcdMostrarMediaTemperatura(float m) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("MEDIA T(10 ult)");
  lcd.setCursor(0, 1);
  lcd.print(m, 1);
  lcd.print(" C");
}

// === LCD error ===
void lcdErrorComs() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SIN COMUNIC.");
  lcd.setCursor(0, 1);
  lcd.print("SATELITE OFF");
}

void setup() {
  Serial.begin(BAUDRATE);
  EmisorSerial.begin(BAUDRATE);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Estacion Tierra");
  lcd.setCursor(0, 1);
  lcd.print("Mostrar T/H");

  pinMode(LED_RX_SAT, OUTPUT);
  pinMode(LED_ALARMA_SENSOR, OUTPUT);
  pinMode(LED_ALARMA_COMS, OUTPUT);
  digitalWrite(LED_RX_SAT, LOW);
  digitalWrite(LED_ALARMA_SENSOR, LOW);
  digitalWrite(LED_ALARMA_COMS, LOW);

  pinMode(PIN_KEYPAD, INPUT);

  lastRxMillis = millis();
  Serial.println("READY");
}

void loop() {
  // === RECIBIR DEL SATÉLITE ===
  if (EmisorSerial.available()) {
    String linea = EmisorSerial.readStringUntil('\n');
    linea.trim();

    if (linea.length() > 0) {
      Serial.println(linea);           // reenviar a PC
      lastRxMillis = millis();         // reset timeout

      digitalWrite(LED_RX_SAT, HIGH);
      digitalWrite(LED_ALARMA_COMS, LOW);

      // VALIDAR CHECKSUM
      int posAst = linea.lastIndexOf('*');
      if (posAst > 0) {
        String cuerpo = linea.substring(0, posAst);
        String csStr = linea.substring(posAst + 1);
        uint8_t csRec = csStr.toInt();
        uint8_t csCalc = calcularChecksum(cuerpo);

        if (csRec == csCalc) {
          digitalWrite(LED_ALARMA_SENSOR, LOW);  // checksum OK

          // PARSEAR MENSAJE G6:1:t:h  etc.
          if (cuerpo.startsWith(GRUPO)) {
            String payload = cuerpo.substring(GRUPO.length());
            int p1 = payload.indexOf(':');
            if (p1 > 0) {
              String codigo = payload.substring(0, p1);
              String resto  = payload.substring(p1 + 1);

              // TEMPERATURA Y HUMEDAD (1:t:h)
              if (codigo == "1") {
                int p2 = resto.indexOf(':');
                if (p2 > 0) {
                  String tStr = resto.substring(0, p2);
                  String hStr = resto.substring(p2 + 1);
                  float t = tStr.toFloat();
                  float h = hStr.toFloat();

                  // guardar últimas lecturas
                  ultimaTemp = t;
                  ultimaHum  = h;

                  // guardar en buffer circular para la media
                  ultimasT[idxT] = t;
                  idxT = (idxT + 1) % N_MEDIA;
                  if (numT < N_MEDIA) numT++;

                  // NO cambiamos la pantalla: la decide el usuario
                  // lcdMostrarTemperaturaHumedad(t, h);
                }
              }

              // ERRORES SENSORES
              if (codigo == "3" || codigo == "6") {
                digitalWrite(LED_ALARMA_SENSOR, HIGH);
                lcd.clear();
                lcd.setCursor(0, 0);
                lcd.print("ERROR SENSOR");
              }
            }
          }
        } else {
          digitalWrite(LED_ALARMA_SENSOR, HIGH);  // checksum malo
        }
      }
    }
  }

  // === BOTONERA ANALÓGICA A0 (A/B/D) ===
  static int lastButton = -1;
  int adc = readAvg(8, 2);

  // si está en reposo, liberar
  if (adc > baseline - PRESS_DELTA) {
    lastButton = -1;
  } else {
    int b = classifyButton(adc);
    if (b != -1 && b != lastButton) {
      char label = LABELS[b];
      if (label == 'A') {
        // última temperatura
        lcdMostrarSoloTemperatura(ultimaTemp);
      } else if (label == 'B') {
        // última humedad
        lcdMostrarSoloHumedad(ultimaHum);
      } else if (label == 'C') {
        // media últimas 10 T
        float m = mediaUltimasT();
        lcdMostrarMediaTemperatura(m);
      }
      lastButton = b;
      delay(200);   // antirrebote
    }
  }

  // === RECIBIR DE PC (PYTHON) ===
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    if (comando.length() > 0) {
      enviarConChecksum(comando);  // reenviar al satélite con checksum
    }
  }

  // === ALARMA SIN COMUNICACIONES ===
  if ((millis() - lastRxMillis) > TIMEOUT_COMS_MS) {
    digitalWrite(LED_RX_SAT, LOW);
    digitalWrite(LED_ALARMA_COMS, HIGH);
    if (!alarmaComsActiva) {
      alarmaComsActiva = true;
      Serial.println("ALARM_COMMS_ON");
      lcdErrorComs();
    }
  } else {
    alarmaComsActiva = false;
  }
}


