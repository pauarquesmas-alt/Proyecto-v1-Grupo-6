#include <SoftwareSerial.h>   // libreria para comunicar por serial extra
#include <DHT.h>              // sensor temp/hum
#include <Servo.h>            // servo motor

// sensor dht11 (el sencillo)
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// pines del ultrasonido y del servo
#define TRIG_PIN 8
#define ECHO_PIN 9
#define SERVO_PIN 6

Servo servo;
int angulo = 0;                 // angulo donde está el servo ahora
bool barridoSubiendo = true;    // para saber si gira pa un lado o pa el otro

// tiempos entre mediciones (los cambia tierra)
unsigned long periodoDist = 120;
unsigned long periodoOrbita = 1000;
unsigned long tNextDist = 0;

// cosas del servo pa que no se mueva de golpe
int objetivoServo = 0;
unsigned long tServoAnterior = 0;

void moverServoSuave(int objetivo) {
  objetivoServo = constrain(objetivo, 0, 180);   // que no se pase del rango
}

void actualizarServo() {
  unsigned long now = millis();
  if (now - tServoAnterior < 15) return;   // no actualizar tan rapido
  tServoAnterior = now;

  if (angulo < objetivoServo) angulo++;    // ir moviendo de 1 en 1 grado
  else if (angulo > objetivoServo) angulo--;
  else return;

  servo.write(angulo);  // mandar el angulo al servo
}

SoftwareSerial mySerial(10, 11); // serial por donde hablamo con tierra

// cosas de enviar temp/hum
unsigned long periodoTH = 5000;
unsigned long proximaLectura = 0;
bool envioTHActivo = true;

// control radar
bool envioRadarActivo = true;

// media de temp
bool usandoMediaEnSatelite = false;
float limiteMedia = 30.0;
float ultimas10[10];
int idx10 = 0, cnt10 = 0;
int consecutivasAltas = 0;

// control de fallos dht
bool esperandoFalloDHT = false;
unsigned long tFalloDHT = 0;
const unsigned long ventanaFallo = 5000;

// fallos seguidos del ultra
int fallosUltraSeguidos = 0;

// modo error pa corromper msgs
bool modoError = false;

// calcular checksum sumando chars
uint8_t calcularChecksum(const String &msg) {
  uint16_t suma = 0;
  for (int i = 0; i < msg.length(); i++) {
    suma += (uint8_t)msg[i];
  }
  return (uint8_t)(suma & 0xFF);
}

// manda mensaje con el checksum al final
void enviarConChecksum(String msg) {
  uint8_t cs = calcularChecksum(msg);
  mySerial.print(msg);
  mySerial.print("*");
  mySerial.println(cs);
}

// para romper un mensaje si está el modo error puesto
String corromperMensaje(const String &msg) {
  if (!modoError) return msg;

  if (msg.length() == 0) return msg;

  String corrupt = msg;
  int idx = random(msg.length());  // cambiar un caracter random
  corrupt[idx] = corrupt[idx] ^ 0x01;

  return corrupt;
}

// mira si el mensaje recibido tiene checksum bien
String validarMensaje(const String &linea) {
  int pos = linea.lastIndexOf('*');
  if (pos < 0) return "";

  String cuerpo = linea.substring(0, pos);
  String cs_str = linea.substring(pos + 1);

  uint8_t cs_recv = cs_str.toInt();
  uint8_t cs_calc = calcularChecksum(cuerpo);

  if (cs_calc == cs_recv) return cuerpo;
  else return "";       // si no coincide lo tiro
}

// mide distancia con el ultra
float medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long dur = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (dur == 0) return -1.0;   // si falla devuelvo -1
  return dur * 0.0343f / 2.0f; // formula velocidad del sonido
}

// cosas de la orbita (física)
const double G = 6.67430e-11;
const double M = 5.97219e24;
const double R_EARTH = 6371000;
const double ALTITUDE = 400000;
const double EARTH_ROTATION_RATE = 7.2921159e-5;
const double TIME_COMPRESSION = 90.0;

unsigned long nextOrbitUpdate = 0;
double real_orbital_period = 0;
double r_orbit = 0;

// calcula posición de la órbita y la imprime
void simulate_orbit(unsigned long ms, double inclination, int ecef) {
  double time = (ms / 1000.0) * TIME_COMPRESSION;
  double angle = 2 * PI * (time / real_orbital_period);

  double x = r_orbit * cos(angle);
  double y = r_orbit * sin(angle) * cos(inclination);
  double z = r_orbit * sin(angle) * sin(inclination);

  if (ecef) {
    double theta = EARTH_ROTATION_RATE * time;
    double x_ecef = x * cos(theta) - y * sin(theta);
    double y_ecef = x * sin(theta) + y * cos(theta);
    x = x_ecef;
    y = y_ecef;
  }

  Serial.print("Time: ");
  Serial.print(time);
  Serial.print(" s | Position: (X: ");
  Serial.print(x);
  Serial.print(" m, Y: ");
  Serial.print(y);
  Serial.print(" m, Z: ");
  Serial.print(z);
  Serial.println(" m)");
}

// setup normal
void setup() {
  Serial.begin(9600);
  mySerial.begin(9600);

  dht.begin();
  servo.attach(SERVO_PIN);
  servo.write(angulo);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  for (int i = 0; i < 10; i++) ultimas10[i] = NAN;

  randomSeed(analogRead(A0));    // semilla pa random

  r_orbit = R_EARTH + ALTITUDE;
  real_orbital_period = 2 * PI * sqrt(pow(r_orbit, 3) / (G * M));
  nextOrbitUpdate = periodoOrbita;
}

// loop principal
void loop() {
  unsigned long now = millis();

  // actualizar órbita cada x tiempo
  if (now >= nextOrbitUpdate) {
    simulate_orbit(now, 0, 0);
    nextOrbitUpdate = now + periodoOrbita;
  }

  // leer temp y hum
  if (envioTHActivo && now >= proximaLectura) {
    proximaLectura = now + periodoTH;

    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
      if (!esperandoFalloDHT) {
        esperandoFalloDHT = true;
        tFalloDHT = now + ventanaFallo;
      }
    } else {
      esperandoFalloDHT = false;

      String msg = "1:" + String(t, 1) + ":" + String(h, 1);
      msg = corromperMensaje(msg);
      enviarConChecksum(msg);

      // si tenemos activada la media
      if (usandoMediaEnSatelite) {
        ultimas10[idx10] = t;
        idx10 = (idx10 + 1) % 10;
        if (cnt10 < 10) cnt10++;

        float sum = 0;
        int n = 0;
        for (int i = 0; i < 10; i++) {
          if (!isnan(ultimas10[i])) {
            sum += ultimas10[i];
            n++;
          }
        }

        if (n > 0) {
          float media = sum / n;

          String msgM = "4:" + String(media, 2);
          msgM = corromperMensaje(msgM);
          enviarConChecksum(msgM);

          if (media > limiteMedia) consecutivasAltas++;
          else consecutivasAltas = 0;

          if (consecutivasAltas >= 3) {
            enviarConChecksum("5:");
            consecutivasAltas = 0;
          }
        }
      }
    }
  }

  // si el dht lleva un rato fallando
  if (esperandoFalloDHT && (long)(now - tFalloDHT) >= 0) {
    enviarConChecksum("3:");
    esperandoFalloDHT = false;
  }

  // radar ultrasonido
  if (envioRadarActivo && (long)(now - tNextDist) >= 0) {
    tNextDist = now + periodoDist;

    float d = medirDistancia();
    if (d < 0) {
      if (++fallosUltraSeguidos >= 3) {
        enviarConChecksum("6:");
        fallosUltraSeguidos = 0;
      }
    } else {
      fallosUltraSeguidos = 0;
      if (d > 50) d = 50;

      String msg = "2:" + String(d, 1) + ":" + String(angulo);
      msg = corromperMensaje(msg);
      enviarConChecksum(msg);
    }

    // barrido automatico del servo
    if (envioRadarActivo && !modoManual()) {
      if (barridoSubiendo) {
        int next = angulo + 2;
        if (next >= 180) {
          next = 180;
          barridoSubiendo = false;
        }
        moverServoSuave(next);
      } else {
        int next = angulo - 2;
        if (next <= 0) {
          next = 0;
          barridoSubiendo = true;
        }
        moverServoSuave(next);
      }
    }
  }

  // actualizar servo suavemente
  actualizarServo();

  // comandos que llegan desde tierra
  if (mySerial.available()) {
    String linea = mySerial.readStringUntil('\n');
    linea.trim();

    String comando = validarMensaje(linea);
    if (comando == "") return;

    int fin = comando.indexOf(':');
    if (fin > 0) {
      int codi = comando.substring(0, fin).toInt();
      String valor = comando.substring(fin + 1);

      // varios comandos que ya teniamos
      if (codi == 1) periodoTH = valor.toInt() * 1000UL;
      else if (codi == 2) {
        int ang = constrain(valor.toInt(), 0, 180);
        moverServoSuave(ang);
        setModoManual(true);
      }
      else if (codi == 3) envioTHActivo = !envioTHActivo;
      else if (codi == 4) usandoMediaEnSatelite = true;
      else if (codi == 5) limiteMedia = valor.toFloat();
      else if (codi == 7) setModoManual(false);
      else if (codi == 8) envioRadarActivo = !envioRadarActivo;
      else if (codi == 9) modoError = !modoError;
      else if (codi == 10) periodoDist = valor.toInt();    // cambiar intervalo radar
      else if (codi == 11) periodoOrbita = valor.toInt();  // cambiar periodo orbita
    }
  }
}

// modo manual para que tierra mueva el servo
bool _modoManual = false;
bool modoManual() { return _modoManual; }
void setModoManual(bool m) { _modoManual = m; }
