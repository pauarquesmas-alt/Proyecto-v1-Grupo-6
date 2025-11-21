#include <SoftwareSerial.h>

SoftwareSerial LoRa(10, 11);  // 10 RX, 11 TX

void setup() {
  Serial.begin(9600);
  LoRa.begin(9600);

  Serial.println("EMISOR INICIAT");
}

void loop() {
  LoRa.println("HOLA LORA");
  Serial.println("Enviat: HOLA LORA");
  delay(1000);
}
