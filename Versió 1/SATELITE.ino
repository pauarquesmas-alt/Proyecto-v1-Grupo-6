#include <SoftwareSerial.h>
#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT11

// Sèrie al terra (satèl·lit: RX=10, TX=11)
SoftwareSerial mySerial(10, 11); // RX, TX

// LED opcional per indicar que s'ha enviat una lectura correcta
const int led1 = 12;

DHT dht(DHTPIN, DHTTYPE);

// Temporitzadors
unsigned long nextHT = 0;                  // proper instant per provar lectura DHT
const unsigned long periodoHT = 3000;      // cada 3 s
bool esperandoTimeout = false;             // estem esperant confirmar el fallo?
unsigned long nextTimeoutHT = 0;           // límit per confirmar fallo (ara + 5 s)
const unsigned long ventanaFallo = 5000;   // 5 s per confirmar l'alarma

void setup() {
  pinMode(led1, OUTPUT);
  digitalWrite(led1, LOW);

  Serial.begin(9600);      // debug a PC (opcional)
  mySerial.begin(9600);    // enllaç amb el terra
  dht.begin();

  nextHT = millis();       // arrencar el cicle de lectures
}

void loop() {
  // --- Tasques periòdiques: lectura de DHT ---
  if (millis() >= nextHT) {
    nextHT = millis() + periodoHT;

    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
      // Lectura KO: inicia (o manté) finestra d'espera de 5 s per confirmar fallo
      if (!esperandoTimeout) {
        esperandoTimeout = true;
        nextTimeoutHT = millis() + ventanaFallo;
        // Opcional: missatge de debug
        Serial.println("DHT KO: iniciant finestra de 5s per confirmar 'Fallo'");
      }
      // No enviem res al terra encara, esperem a confirmar el fallo
    } else {
      // Lectura OK: cancel·la qualsevol espera d'alarma i envia dades
      esperandoTimeout = false;

      // Enviament cap al terra (format que demana la GUI)
      mySerial.print("T:");
      mySerial.print(t, 1);       // 1 decimal
      mySerial.print(":H:");
      mySerial.println(h, 1);     // 1 decimal

      // Indicar enviament correcte amb un parpelleig curt
      digitalWrite(led1, HIGH);
      delay(80);
      digitalWrite(led1, LOW);

      // Debug opcional a Serial
      Serial.print("OK -> T:");
      Serial.print(t, 1);
      Serial.print(" :H:");
      Serial.println(h, 1);
    }
  }

  Confirmació d'alarma per lectura fallida ---
  if (esperandoTimeout && (millis() >= nextTimeoutHT)) {
    // Han passat 5 s sense cap lectura bona -> enviem alarma
    mySerial.println("Fallo");    
    Serial.println("Enviat 'Fallo' al terra");
    esperandoTimeout = false;
  }

  
}
