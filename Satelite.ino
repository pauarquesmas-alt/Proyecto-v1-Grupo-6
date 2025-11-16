#include <SoftwareSerial.h>
#include <DHT.h>
#include <Servo.h>

// ====== DHT11 ======
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ====== Ultrasonido + Servo ======
#define TRIG_PIN 8
#define ECHO_PIN 9
#define SERVO_PIN 6

Servo servo;
int angulo = 0;                 // 0..180
bool barridoSubiendo = true;    // controlar el barrido 0..180
unsigned long periodoDist = 120; // ms entre medidas de distancia (barrido fluido)
unsigned long tNextDist = 0;

// ====== Comunicación ======
SoftwareSerial mySerial(10, 11); // RX, TX (enlace con Tierra)

// ====== Parámetros T/H y medias ======
unsigned long periodoTH = 5000;   // ms
unsigned long proximaLectura = 0;
bool envioTHActivo = true;

bool usandoMediaEnSatelite = false;      // se activa al recibir "4:"
float limiteMedia = 30.0;
float ultimas10[10];                      // buffer circular para medias
int idx10 = 0, cnt10 = 0;
int consecutivasAltas = 0;

// Control fallo DHT
bool esperandoFalloDHT = false;
unsigned long tFalloDHT = 0;
const unsigned long ventanaFallo = 5000; // 5 s para confirmar fallo

// Debounce del fallo ultrasonido (evitar falsos)
int fallosUltraSeguidos = 0;

void setup() {
  Serial.begin(9600);
  mySerial.begin(9600);

  dht.begin();

  servo.attach(SERVO_PIN);
  servo.write(angulo);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // inicializar buffer medias
  for (int i=0;i<10;i++) ultimas10[i] = NAN;
}

static float medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 30000UL); // 30ms ~ 5m
  if (dur == 0) return -1.0;                   // timeout -> fallo
  float d = dur * 0.0343f / 2.0f;              // cm
  return d;
}

void loop() {
  unsigned long now = millis();

  // ===== Enviar T/H =====
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

      // Mensaje hacia tierra: 1:<temp>:<hum>
      mySerial.print("1:");
      mySerial.print(t, 1);
      mySerial.print(":");
      mySerial.println(h, 1);

      // Si nos han pedido que el satélite calcule medias -> 4:<media>
      if (usandoMediaEnSatelite) {
        ultimas10[idx10] = t;
        idx10 = (idx10 + 1) % 10;
        if (cnt10 < 10) cnt10++;

        // calcular media de las válidas
        float sum=0; int n=0;
        for (int i=0;i<10;i++){
          if (!isnan(ultimas10[i])) { sum += ultimas10[i]; n++; }
        }
        if (n > 0) {
          float media = sum / n;
          mySerial.print("4:");
          mySerial.println(media, 2);

          if (media > limiteMedia) consecutivasAltas++;
          else consecutivasAltas = 0;

          if (consecutivasAltas >= 3) {
            mySerial.println("5:");  // alarma a tierra
            consecutivasAltas = 0;   // reinicia
          }
        }
      }
    }
  }

  // ===== Confirmación de fallo DHT =====
  if (esperandoFalloDHT && (long)(now - tFalloDHT) >= 0) {
    mySerial.println("3:");
    esperandoFalloDHT = false;
  }

  // ===== Barrido + envío de distancia =====
  if ((long)(now - tNextDist) >= 0) {
    tNextDist = now + periodoDist;

    float d = medirDistancia();
    if (d < 0) {
      if (++fallosUltraSeguidos >= 3) { // tres timeouts seguidos
        mySerial.println("6:");
        fallosUltraSeguidos = 0;
      }
    } else {
      fallosUltraSeguidos = 0;
      // recorte a 0..50 para el radar
      if (d < 0) d = 0;
      if (d > 50) d = 50;

      // Mensaje: 2:<dist_cm>:<angulo_deg>
      mySerial.print("2:");
      mySerial.print(d, 1);
      mySerial.print(":");
      mySerial.println(angulo);
    }

    // Movimiento del servo (barrido automático 0..180)
    if (!usandoMediaEnSatelite) { /* nada que ver, solo ejemplo de uso de flag */ }
    // el modo automático se desactiva sólo si nos ordenan una orientación manual
    // (ver comandos). Si el PC envía "7:" volvemos a automático.
    if (barridoSubiendo && !modoManual()) {
      angulo += 2;
      if (angulo >= 180) { angulo = 180; barridoSubiendo = false; }
      servo.write(angulo);
    } else if (!barridoSubiendo && !modoManual()) {
      angulo -= 2;
      if (angulo <= 0) { angulo = 0; barridoSubiendo = true; }
      servo.write(angulo);
    }
  }

  // ===== Recepción de comandos =====
  if (mySerial.available()) {
    String comando = mySerial.readStringUntil('\n');
    comando.trim();
    int fin = comando.indexOf(':');

    if (fin > 0) {
      int codi = comando.substring(0, fin).toInt();
      String valor = comando.substring(fin + 1);

      if (codi == 1) {                       // periodo T/H (seg)
        unsigned long s = valor.toInt();
        if (s >= 1) periodoTH = s * 1000UL;

      } else if (codi == 2) {                // orientación manual
        int ang = valor.toInt();
        ang = constrain(ang, 0, 180);
        servo.write(ang);
        angulo = ang;
        setModoManual(true);

      } else if (codi == 3) {                // parar/reanudar envío T/H
        envioTHActivo = !envioTHActivo;

      } else if (codi == 4) {                // activar cálculo de medias en satélite
        usandoMediaEnSatelite = true;

      } else if (codi == 5) {                // actualizar límite de alarma de media
        limiteMedia = valor.toFloat();

      } else if (codi == 7) {                // volver a barrido 0..180
        setModoManual(false);
      }
    }
  }
}

/*** pequeño gestor del modo manual/auto (variable privada) ***/
bool _modoManual = false;
bool modoManual() { return _modoManual; }
void setModoManual(bool m) { _modoManual = m; }

