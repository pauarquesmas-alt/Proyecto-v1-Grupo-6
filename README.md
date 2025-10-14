# Proyecto-v1

# Proyecto Estación de Tierra - Versión 1

## 📋 Descripción
Proyecto que conecta un Arduino "controlador" (satélite) con un Arduino "estación de tierra".  
El satélite mide **temperatura y humedad** y envía los datos por serie.  
La estación de tierra los recibe y los muestra en una **gráfica dinámica** en una interfaz Python.

## ⚙️ Archivos incluidos
- **arduino_satellite.ino** → Lee sensores (DHT o similar) y envía datos por Serial.
- **arduino_ground.ino** → Recibe datos del satélite y los reenvía al PC.
- **interfaz_grafica.py** → Interfaz con gráfica incrustada y control Start/Stop.
- **README.md** → Este documento.

## ▶️ Cómo ejecutarlo
1. **Sube** los códigos a los Arduinos.
2. **Ejecuta** `python interfaz_grafica.py`.
3. Verás los valores de temperatura y humedad en una gráfica en tiempo real.
4. El botón **Start/Stop** permite pausar o reanudar la lectura.

## 🚨 Alarmas
- Si el sensor no funciona → el Arduino satélite envía un mensaje de error.
- Si no hay comunicación → la interfaz muestra un aviso en pantalla.

## 🧪 Video demostración
[Enlace al vídeo (máx. 5 minutos)](https://...)

## 🏷️ Versión
Tag en GitHub: `v1.0`
