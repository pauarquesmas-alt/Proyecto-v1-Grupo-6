#include <SoftwareSerial.h>   // libreria pa usar otro puerto serie

// leds para ver cosas del satelite
#define LED_RX_SAT 13           // este se enciende si llega algo
#define LED_ALARMA_SENSOR 6     // alarma del sensor si envia codigos raros
#define LED_ALARMA_COMS 7       // alarma cuando no hay coms

#define BAUDRATE 9600           // velocidad del puerto
#define TIMEOUT_COMS_MS 5000    // tiempo max sin recibir nada

SoftwareSerial EmisorSerial(10, 11); // serie secundario (10 es RX y 11 TX)
unsigned long lastRxMillis = 0;      // cuando recibimos lo ultimo

// calculo del checksum (suma simple de chars)
uint8_t calcularChecksum(String msg) {
  uint16_t suma = 0;
  for (char c : msg) suma += (uint8_t)c;   // voy sumando cada caracter
  return (uint8_t)(suma & 0xFF);           // me quedo con el byte de abajo
}

// manda el mensaje y le pone el checksum detras
void enviarConChecksum(String msg) {
  uint8_t cs = calcularChecksum(msg);
  EmisorSerial.print(msg);      // mando el mensaje normal
  EmisorSerial.print("*");      // separador
  EmisorSerial.println(cs);     // checksum al final
}

void setup() {
  Serial.begin(BAUDRATE);        // serie normal (pc)
  EmisorSerial.begin(BAUDRATE);  // serie hacia el satelite

  // pongo los leds como salida
  pinMode(LED_RX_SAT, OUTPUT);
  pinMode(LED_ALARMA_SENSOR, OUTPUT);
  pinMode(LED_ALARMA_COMS, OUTPUT);

  // los apago al inicio
  digitalWrite(LED_RX_SAT, LOW);
  digitalWrite(LED_ALARMA_SENSOR, LOW);
  digitalWrite(LED_ALARMA_COMS, LOW);

  lastRxMillis = millis();       // guardo el tiempo actual
  Serial.println("READY");       // mensajito pa saber que arranco
}

void loop() {

  // cuando llega algo del satelite lo leemos
  if (EmisorSerial.available()) {

    String linea = EmisorSerial.readStringUntil('\n');  
    linea.trim();   // quito saltos de linea

    if (linea.length() > 0) {    // si hay texto

      Serial.println(linea);     // lo mando al pc pa verlo
      lastRxMillis = millis();   // actualizo el reloj de cuando recibí

      digitalWrite(LED_RX_SAT, HIGH);  // led de "todo ok"
      digitalWrite(LED_ALARMA_COMS, LOW);

      // si el satelite manda un codigo de error del sensor
      if (linea.startsWith("3:") || linea.startsWith("6:"))
        digitalWrite(LED_ALARMA_SENSOR, HIGH);
      else
        digitalWrite(LED_ALARMA_SENSOR, LOW);
    }
  }

  // aqui leo lo que manda python por el puerto serie normal
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');  
    comando.trim();

    if (comando.length() > 0) {
      EmisorSerial.println(comando);   // lo reenviamos al satelite tal cual
    }
  }

  // si pasa mucho tiempo sin recibir nada, encendemos la alarma
  if ((millis() - lastRxMillis) > TIMEOUT_COMS_MS) {
    digitalWrite(LED_RX_SAT, LOW);         // se apaga el led de recepción
    digitalWrite(LED_ALARMA_COMS, HIGH);   // y se prende la alarma
    Serial.println("ALARM_COMMS_ON");      // aviso para python
  }
}
