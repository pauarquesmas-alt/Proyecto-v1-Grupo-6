#include <Arduino.h>

const uint8_t PIN_KEYPAD = A0;

const int N_BUTTONS = 5;
const char LABELS[N_BUTTONS] = { 'A', 'B', 'C', 'D', 'E' };

const int PRESS_DELTA = 60;
const int TOLERANCE   = 30;

int baseline = 1023;
int refVal[N_BUTTONS];

int readAvg(int n = 10, int dlyMs = 2) {
  long sum = 0;
  for (int i = 0; i < n; i++) {
    sum += analogRead(PIN_KEYPAD);
    delay(dlyMs);
  }
  return (int)(sum / n);
}

void waitRelease() {
  // espera a que vuelva cerca del reposo
  while (readAvg(5, 2) < baseline - (PRESS_DELTA / 2)) {
    delay(10);
  }
}

int captureStable(int maxWaitMs = 4000) {
  // captura una media cuando la lectura es razonablemente estable
  unsigned long t0 = millis();
  while (millis() - t0 < (unsigned long)maxWaitMs) {
    int minV = 1023, maxV = 0;
    long sum = 0;
    const int N = 20;

    for (int i = 0; i < N; i++) {
      int v = analogRead(PIN_KEYPAD);
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
      sum += v;
      delay(3);
    }

    if ((maxV - minV) <= 8) {        // estable
      return (int)(sum / N);
    }
    delay(10);
  }
  return -1;
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

void calibrate() {
  Serial.println(F("=== CALIBRACION BOTONERA ==="));
  Serial.println(F("No pulses nada..."));
  delay(300);

  baseline = readAvg(50, 2);
  Serial.print(F("Reposo ADC = "));
  Serial.println(baseline);

  for (int i = 0; i < N_BUTTONS; i++) {
    Serial.print(F("Pulsa y MANTEN el boton "));
    Serial.print(LABELS[i]);
    Serial.println(F(" ..."));

    // esperar pulsación: en estas botoneras suele bajar respecto al reposo
    while (readAvg(5, 2) > baseline - PRESS_DELTA) {
      delay(10);
    }

    int v = captureStable();
    if (v < 0) {
      Serial.println(F("ERROR: no se pudo capturar estable. Reinicia y prueba de nuevo."));
      while (true) {}
    }

    refVal[i] = v;
    Serial.print(F("Guardado "));
    Serial.print(LABELS[i]);
    Serial.print(F(" = "));
    Serial.println(refVal[i]);

    Serial.println(F("Suelta el boton..."));
    waitRelease();
    delay(200);
  }

  Serial.println(F("=== LISTO ==="));
  Serial.println(F("Pulsa botones y se imprimira A/B/C/D/E"));
  Serial.println();
}

void setup() {
  Serial.begin(9600);      // <- Pon el Monitor Serie a 9600
  calibrate();
}

void loop() {
  static int lastPrinted = -1;

  int adc = readAvg(8, 2);

  // si no está pulsado, resetea para permitir imprimir en la siguiente pulsación
  if (adc > baseline - PRESS_DELTA) {
    lastPrinted = -1;
    delay(20);
    return;
  }

  int b = classifyButton(adc);

  if (b != -1 && b != lastPrinted) {
    Serial.println(LABELS[b]);
    lastPrinted = b;
  }

  delay(30);
}
