// **ARDUINO RECEPTOR/CONTROLADOR (Conectado a la PC - COM4)**
// Este sketch recibe los datos del Arduino Emisor (DHT) a través de SoftwareSerial
// y los reenvía a Python. También recibe el comando 'P' de Python para parpadear el LED.

#include <SoftwareSerial.h>

// --- CONFIGURACIÓN DE PINES Y VELOCIDADES ---
#define LED_PIN 13              // LED integrado
#define LED_FALLO_SENSOR 8      // LED para alarma de "Fallo"
#define LED_FALLO_COMS 9        // LED para fallo de comunicación
#define BLINK_DURATION_MS 100
#define BAUDRATE 9600

SoftwareSerial EmisorSerial(10, 11); // RX, TX desde el satélite

// --- VARIABLES DE ESTADO ---
int isBlinking = 0;
unsigned long lastBlinkTime = 0;

// Variables para la detección de fallo de comunicación
unsigned long lastRxTime = 0;
const unsigned long TIMEOUT_COMS = 5000; // 5 segundos sin recibir -> alarma

void setup() {
    Serial.begin(BAUDRATE);      
    EmisorSerial.begin(BAUDRATE); 
    
    pinMode(LED_PIN, OUTPUT);
    pinMode(LED_FALLO_SENSOR, OUTPUT);
    pinMode(LED_FALLO_COMS, OUTPUT);

    digitalWrite(LED_PIN, LOW);
    digitalWrite(LED_FALLO_SENSOR, LOW);
    digitalWrite(LED_FALLO_COMS, LOW);

    lastRxTime = millis();  // empieza el contador
}

void loop() {
    // 1. Reenviar datos del Emisor (satélite) a la PC
    while (EmisorSerial.available()) {
        String mensaje = EmisorSerial.readStringUntil('\n');
        mensaje.trim();
        Serial.println(mensaje);
        lastRxTime = millis();              // reinicia temporizador de comunicación
        digitalWrite(LED_FALLO_COMS, LOW);  // hay comunicación, apaga alarma

        // Si llega "Fallo" -> encender LED de alarma sensor
        if (mensaje.equalsIgnoreCase("Fallo")) {
            digitalWrite(LED_FALLO_SENSOR, HIGH);
        } else {
            digitalWrite(LED_FALLO_SENSOR, LOW);
        }
    }

    // 2. Detectar fallo de comunicación (más de 5 s sin recibir nada)
    if (millis() - lastRxTime > TIMEOUT_COMS) {
        digitalWrite(LED_FALLO_COMS, HIGH);
    }

    // 3. Comando 'P' desde Python (sin cambios)
    if (Serial.available() > 0) {
        char command = Serial.read(); 
        if (command == 'P') { 
            isBlinking = 1;
            lastBlinkTime = millis();
            digitalWrite(LED_PIN, HIGH);
        }
    }

    // 4. Apagar LED tras el pulso
    if (isBlinking == 1) {
        if ((millis() - lastBlinkTime) >= BLINK_DURATION_MS) {
            digitalWrite(LED_PIN, LOW);
            isBlinking = 0;
        }
    }
}
