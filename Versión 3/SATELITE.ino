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
String GRUPO = "G6:";    // <<--- CAMBIA “6” POR TU NÚMERO DE GRUPO

// --------------------- TIEMPOS ----------------------
// Envíos cada 2 segundos (más frecuencia)
unsigned long periodoTH   = 2000;   // antes: 8000
unsigned long periodoDist = 2000;   // antes: 8000

unsigned long proximaLecturaTH   = 0;
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

/* =========================================================
   ===============  SIMULADOR DE ÓRBITA  ===================
   ========================================================= */

// Constants
const double G = 6.67430e-11;       // Gravitational constant
const double M = 5.97219e24;        // Mass of Earth (kg)
const double R_EARTH = 6371000.0;   // Radius of Earth (m)
const double ALTITUDE = 400000.0;   // Altitude (m)

// Ahora: órbita más lenta y suave, actualizada cada 2s
const unsigned long MILLIS_BETWEEN_UPDATES = 2000; // 2 s
const double TIME_COMPRESSION = 30.0;              // 30x (más lenta → círculo más “limpio”)

// Variables
unsigned long nextOrbitUpdate = 0;
double real_orbital_period = 0.0;
double r = 0.0;

// Calcula y envía órbita
void simulate_orbit(unsigned long ms) {
  double time = (ms / 1000.0) * TIME_COMPRESSION; 
  double angle = 2.0 * PI * (time / real_orbital_period);

  double x = r * cos(angle);
  double y = r * sin(angle);
  double z = 0.0;  // órbita ecuatorial plana

  // Enviar por LoRa con checksum (código 4)
  // Formato: 4:time:x:y:z
  enviarConChecksum(
    "4:" + String(time, 1) + ":" +
    String(x, 0) + ":" +
    String(y, 0) + ":" +
    String(z, 0)
  );

  // Debug por USB si quieres verlo
  Serial.print("Orbit -> t=");
  Serial.print(time, 1);
  Serial.print(" x=");
  Serial.print(x, 0);
  Serial.print(" y=");
  Serial.print(y, 0);
  Serial.print(" z=");
  Serial.println(z, 0);
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

  // --- ORBITA: inicialización ---
  r = R_EARTH + ALTITUDE;
  real_orbital_period = 2.0 * PI * sqrt(pow(r, 3) / (G * M));
  nextOrbitUpdate = MILLIS_BETWEEN_UPDATES;

  Serial.println("SATELITE INICIADO CON ÓRBITA");
  Serial.print("Periodo orbital real (s): ");
  Serial.println(real_orbital_period, 1);
}

// --------------------- LOOP --------------------------
void loop() {
  unsigned long now = millis();

  // ----------- ÓRBITA (cada 2s) -----------------------
  if (now >= nextOrbitUpdate) {
    simulate_orbit(now);
    nextOrbitUpdate = now + MILLIS_BETWEEN_UPDATES;
  }

  // ----------- TEMPERATURA/HUMEDAD (cada 2s) ----------
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

  // ----------- DISTANCIA (cada 2s) --------------------
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
