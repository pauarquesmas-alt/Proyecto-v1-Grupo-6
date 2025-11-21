/* TEST UNITARIO: Servo 0-180°
*/
#include <Servo.h>
Servo s;
int objetivo = 0;

void setup() {
  Serial.begin(9600);
  s.attach(9);
  s.write(0);
  delay(500);
  Serial.println(F("TEST_SERVO:START"));
  // Autoprueba: 0->90->180->90->0
  int seq[] = {0, 90, 180, 90, 0};
  for (int i=0;i<5;i++){ s.write(seq[i]); delay(500); }
  Serial.println(F("TEST_SERVO:PASS"));
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if (cmd.startsWith("SET:")) {
      int ang = cmd.substring(4).toInt();
      ang = constrain(ang, 0, 180);
      objetivo = ang;
      s.write(objetivo);
      delay(400);
      Serial.print(F("ACK:"));
      Serial.println(objetivo);
    }
  }
}
