/* TEST UNITARIO: Lógica de alarma por medias
*/
const uint8_t V = 10;
float buf[V]; uint8_t n = 0, llen = 0;
float umbral = 25.0; // editable
uint8_t consecutivas = 0;

void push(float t){
  buf[n] = t; n = (n+1)%V; if (llen<V) llen++;
}
bool media(float& out){
  if (llen<V) return false;
  float s=0; for (uint8_t i=0;i<V;i++) s+=buf[i];
  out = s/V; return true;
}

void resetState(){
  n=0; llen=0; consecutivas=0;
}

void setup(){
  Serial.begin(9600);
  Serial.println(F("TEST_ALARM:START"));
}

void loop(){
  if (Serial.available()){
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if (cmd.startsWith("UMBRAL:")){
      umbral = cmd.substring(8).toFloat();
      Serial.print(F("ACK_UMBRAL:")); Serial.println(umbral,1);
    } else if (cmd=="RUN"){
      resetState();
      // Secuencia: 12 valores > umbral para asegurar 3 medias consecutivas altas
      for (int i=0;i<12;i++){
        push(umbral + 5.0); // mayor que umbral
        float m; if (media(m)){
          if (m>umbral) consecutivas++; else consecutivas=0;
          if (consecutivas>=3){
            Serial.println(F("5:"));                // alarma
            Serial.println(F("TEST_ALARM:PASS"));
            return;
          }
        }
        delay(100);
      }
      Serial.println(F("TEST_ALARM:FAIL"));
    }
  }
}
