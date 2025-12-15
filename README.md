# Proyecto Grupo 6

# Versión 1

## 📋 Descripción
<p align="justify">
Proyecto que conecta un Arduino "controlador" (satélite) con un Arduino "estación de tierra".  
El satélite mide **temperatura y humedad** y envía los datos por serie.  
La estación de tierra los recibe y los muestra en una **gráfica dinámica** en una interfaz Python.
</p>

## 🧪 Video demostración
https://youtu.be/FFqi9oINteE

# Versión 2
## 📋 Descripción
<p align="justify">
El proyecto implementa una estación de tierra conectada a un “satélite” Arduino que mide temperatura, humedad y distancia con ultrasonidos. Desde el ordenador, una interfaz en Python muestra en tiempo real las gráficas de T/H y la media móvil, controla el periodo de envío de datos y el movimiento del servo, dibuja un radar con la distancia detectada y lanza alarmas cuando las medias de temperatura superan un umbral o se detectan fallos en los sensores.
</p>

## 🧪 Video demostración
https://youtu.be/GcaQ2BR3xfE?si=nUMKSqZa3t8V-v8U

# Versión 3
## 📋 Descripción
<p align="justify">
Las novedades principales de la versión 3 son: un sistema de detección de errores en la comunicación, el envío por parte del satélite de datos sobre su posición que se mostrarán en una gráfica apropiada, la implementación de un sistema de comunicación inalámbrica entre el satélite y la estación de tierra y la implementación de un sistema de registro de eventos.
</p>

## 🧪 Video demostración
https://youtu.be/kKIEUvKRv5c

# Versión 4
## 📋 Descripción
<p align="justify">
Se incorpora mejoras avanzadas orientadas a ofrecer un sistema más profesional, robusto y eficiente. Se ha rediseñado completamente la interfaz gráfica de la estación de tierra y se ha añadido un sistema de inicio de sesión que profesionaliza el acceso y el control del satélite.
Se ha implementado una nueva pantalla de monitorización que muestra la última temperatura y humedad recibidas, así como la media de las diez últimas temperaturas, con control total mediante una botonera desde tierra. Las gráficas se han optimizado para representar únicamente los diez valores más recientes, mejorando la claridad y el rendimiento.
Asimismo, se ha optimizado la comunicación LoRa para evitar la saturación del canal, garantizando una transmisión estable y fiable. Todas estas mejoras han sido desarrolladas tras corregir e implementar íntegramente las sugerencias recibidas en versiones anteriores, consolidando un sistema final de alto nivel técnico.
</p>

## 🧪 Video demostración

