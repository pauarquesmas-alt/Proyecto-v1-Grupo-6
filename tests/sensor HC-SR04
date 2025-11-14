/* TEST UNITARIO: HC-SR04 
*/
#define TRIG_PIN 6
#define ECHO_PIN 7

const uint8_t FALLOS_UMBRAL = 5;
uint8_t fallos = 0;

long medirDistanciaCm() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 30000UL); // timeout 30 ms
  if (dur == 0) return -1;
  return (long)((dur / 2.0) / 29.1);
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.begin(9600);
  delay(1000);
  Serial.println(F("TEST_US:START"));
}

void loop() {
  long d = medirDistanciaCm();
  if (d < 0 || d > 400) {
    fallos++;
    Serial.println(F("7:"));             // fallo
    if (fallos >= FALLOS_UMBRAL) {
      Serial.println(F("TEST_US:FAIL"));
      while (1) {}
    }
  } else {
    fallos = 0;
    Serial.print(F("6:"));               // formato de datos de distancia
    Serial.println(d);
    if (d >= 0 && d <= 400) {
      Serial.println(F("TEST_US:PASS"));
    }
  }
  delay(300);
}
