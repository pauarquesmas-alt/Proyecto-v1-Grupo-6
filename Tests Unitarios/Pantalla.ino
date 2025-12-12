#include <Wire.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x3F, 16, 2); 

void setup() {
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("LCD OK (0x3F)");
}

void loop() {
  static int n = 0;
  lcd.setCursor(0,1);
  lcd.print("Contador: ");
  lcd.print(n++);
  lcd.print("   ");
  delay(500);
}
