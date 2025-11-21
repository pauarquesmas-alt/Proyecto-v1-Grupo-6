#include <SoftwareSerial.h>
#include <DHT.h>
#include <Servo.h>

// --------------------- CONFIGURACIÓN ----------------------
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

#define TRIG_PIN 8
#define ECHO_PIN 9
#define SERVO_PIN 6

SoftwareSerial mySerial(10, 11);  // LoRa
Servo servo;

// ==== IDENTIFICADOR DE GRUPO ====
String GRUPO = "G6:";    // <<--- CAMBIA “4” POR TU NÚMERO DE GRUPO

// --------------------- TIEMPOS ----------------------
// Envíos cada 8 segundos
unsigned long periodoTH = 8000;
unsigned long periodoDist = 8000;

unsigned long proximaLecturaTH = 0;
unsigned long proximaLecturaDist = 0;

bool envioTHActivo = true;
bool envioRadarActivo = true;

int angulo = 0;
int objetivoServo = 0;
unsigned long tServoAnterior = 0;

// Servo tarda 20s en recorrer 180° → 111ms por grado
const unsigned long servoStepTime = 111;

// ------------------- CHECKSUM ----------------------
uint8_t calcularChecksum(const String &msg) {
  uint16_t s = 0;
  for (char c : msg) s += c;
  return (uint8_t)(s & 0xFF);
}

void enviarConChecksum(String msg) {
  String full = GRUPO + msg;   // AÑADE TU IDENTIFICADOR
  uint8_t cs = calcularChecksum(full);
  mySerial.print(full);
  mySerial.print("*");
  mySerial.println(cs);
}

// ------------------- ULTRASONIDO ----------------------
float medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long dur = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (dur == 0) return -1;
  return dur * 0.0343f / 2.0f;
}

// ------------------- SERVO SUAVE ----------------------
void moverServoSuave(int objetivo) {
  objetivoServo = constrain(objetivo, 0, 180);
}

void actualizarServo() {
  unsigned long now = millis();
  if (now - tServoAnterior < servoStepTime) return;
  tServoAnterior = now;

  if (angulo < objetivoServo) angulo++;
  else if (angulo > objetivoServo) angulo--;
  else return;

  servo.write(angulo);
}

// -------------------- SETUP -------------------------
void setup() {
  Serial.begin(9600);    // solo para debug
  mySerial.begin(9600);  // LoRa

  dht.begin();
  servo.attach(SERVO_PIN);
  servo.write(angulo);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println("SATELITE INICIADO (sin órbita)");
}

// --------------------- LOOP --------------------------
void loop() {
  unsigned long now = millis();

  // ----------- TEMPERATURA/HUMEDAD (cada 8s) ----------
  if (envioTHActivo && now >= proximaLecturaTH) {
    proximaLecturaTH = now + periodoTH;

    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
      enviarConChecksum("3:");  // error DHT
    } else {
      enviarConChecksum("1:" + String(t,1) + ":" + String(h,1));
    }
  }

  // ----------- DISTANCIA (cada 8s) --------------------
  if (envioRadarActivo && now >= proximaLecturaDist) {
    proximaLecturaDist = now + periodoDist;

    float d = medirDistancia();
    if (d < 0) {
      enviarConChecksum("6:");  // error ultra
    } else {
      if (d > 50) d = 50;
      enviarConChecksum("2:" + String(d,1) + ":" + String(angulo));
    }

    // Barrido automático suave
    int next = angulo + (angulo < 180 ? 2 : -2);
    if (next >= 180) next = 180;
    if (next <= 0)   next = 0;
    moverServoSuave(next);
  }

  // ----------- ACTUALIZAR SERVO -----------------------
  actualizarServo();

  // ----------- COMANDOS DESDE TIERRA ------------------
  if (mySerial.available()) {
    String linea = mySerial.readStringUntil('\n');
    linea.trim();

    int pos = linea.indexOf(':');
    if (pos <= 0) return;

    int codi = linea.substring(0,pos).toInt();
    String valor = linea.substring(pos+1);

    if (codi == 1) periodoTH = valor.toInt() * 1000UL;
    if (codi == 2) moverServoSuave(constrain(valor.toInt(),0,180));
    if (codi == 3) envioTHActivo = !envioTHActivo;
    if (codi == 8) envioRadarActivo = !envioRadarActivo;
    if (codi == 10) periodoDist = valor.toInt();
  }
}
