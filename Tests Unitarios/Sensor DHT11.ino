/* TEST UNITARIO: DHT11 (T/H)
*/
#include <DHT.h>
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

void setup(){
  Serial.begin(9600);
  dht.begin();
  delay(1500);
  Serial.println(F("TEST_DHT:START"));
}

void loop(){
  float h = dht.readHumidity();
  float t = dht.readTemperature(); // °C
  if (isnan(h) || isnan(t)){
    Serial.println(F("3:"));
    Serial.println(F("TEST_DHT:FAIL"));
  } else {
    bool ok = (h>=0 && h<=100 && t>=-20 && t<=80);
    Serial.print(F("1:")); Serial.print(t,1);
    Serial.print(F(":"));  Serial.println(h,1);
    if (ok) Serial.println(F("TEST_DHT:PASS"));
    else    Serial.println(F("TEST_DHT:FAIL"));
  }
  delay(1500);
}
