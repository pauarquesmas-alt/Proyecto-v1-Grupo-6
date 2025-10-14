#include <SoftwareSerial.h>
#include <DHT.h>
#define DHTPIN 2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);
SoftwareSerial mySerial(10, 11); // RX, TX 
const int led1 = 12;  // LED

// variables pedidas
unsigned long nextHT = 0;
bool esperandoTimeout = false;
unsigned long nextTimeoutHT = 0;

void setup() {
  pinMode(led1, OUTPUT);
  digitalWrite(led1, LOW);

  mySerial.begin(9600);  // hacia la estación de tierra
  Serial.begin(9600);    // depuración opcional al PC
  dht.begin();

  nextHT = millis();     // primera lectura inmediata
}

void loop() {
  // otras tareas...

  if (millis() >= nextHT) {
    nextHT = millis() + 3000;  // ritmo ~3 s (ajusta si quieres)

    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
      // lectura inválida -> inicia/renueva ventana de 5 s
      esperandoTimeout = true;
      nextTimeoutHT = millis() + 5000; // 5 segundos
    } else {
      // lectura válida -> cancelar ventana y enviar datos
      esperandoTimeout = false;

      digitalWrite(led1, HIGH);
      mySerial.print("T: ");
      mySerial.print(t);
      mySerial.print(":H:");
      mySerial.println(h);
      digitalWrite(led1, LOW);
    }
  }

  if (esperandoTimeout && (millis() >= nextTimeoutHT)) {
    mySerial.print("Fallo");     // aviso a la estación de tierra
    esperandoTimeout = false;    // evitar repetir hasta nuevo fallo
  }

  // otras tareas...
}

