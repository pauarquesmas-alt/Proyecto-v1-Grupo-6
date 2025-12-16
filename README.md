# Proyecto Grupo 6
# El equipo
<p align="justify">
Latorre Magliocco, Giulia
<br><br>
Arques Mas, Pau
<br><br>
Sambró Gómez, Aina
</p>

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
## 🚀 Sistema Satelital – Versión 4

La **Versión 4** introduce un conjunto de **mejoras avanzadas** que elevan el sistema a un nivel más profesional y completo. Entre las principales novedades destacan el **rediseño integral de la interfaz gráfica de la estación de tierra**, la incorporación de un **sistema de inicio de sesión** para controlar el acceso al satélite, una **nueva pantalla de monitorización avanzada** que muestra los últimos valores recibidos y la media de las diez últimas temperaturas, así como la **optimización de las gráficas**, limitadas a los valores más recientes para mejorar la claridad y el rendimiento. Además, se ha **optimizado la comunicación LoRa** para evitar la saturación del canal y garantizar una transmisión más estable y fiable. Todas estas mejoras se han implementado tras corregir e integrar las sugerencias recibidas en versiones anteriores.

La Versión 4 consolida así un sistema **completo, estable y técnicamente maduro**, en el que se integran todas las funcionalidades exigidas hasta la Versión 3 junto con estas nuevas aportaciones, siguiendo fielmente los criterios de evaluación definidos en la asignatura.

Desde el punto de vista funcional, el prototipo **cumple íntegramente los requisitos especificados**, implementando la captura, el procesamiento y la transmisión de datos de **temperatura, humedad y posición del satélite**. La comunicación bidireccional con la estación de tierra permite tanto el envío periódico de información como el control remoto del satélite, y su correcto funcionamiento ha sido verificado mediante **pruebas integradas del sistema completo**.

El diseño del sistema prioriza la **robustez**, permitiendo gestionar errores de sensores, posibles fallos en la comunicación y entradas incorrectas del usuario sin provocar bloqueos. De este modo, el sistema mantiene un comportamiento estable y predecible incluso ante situaciones anómalas, reforzando su fiabilidad.

La estación de tierra dispone de una **interfaz gráfica clara e intuitiva**, resultado del rediseño completo realizado en esta versión. La información se presenta de forma ordenada mediante pantallas de monitorización y gráficas optimizadas, mientras que el sistema de inicio de sesión aporta una capa adicional de control y profesionalización. La interacción con el usuario es sencilla y no genera ambigüedades.

El código del satélite y de la estación de tierra está **bien organizado y documentado**, estructurado en funciones claramente definidas y acompañado de comentarios explicativos. Esta organización facilita la comprensión del sistema y permite realizar modificaciones o ampliaciones con un esfuerzo reducido. Asimismo, se han utilizado **algoritmos y estructuras de datos eficientes**, optimizando el rendimiento, la visualización de la información y el uso del canal de comunicación.

Finalmente, la Versión 4 incorpora **funcionalidades adicionales de alto valor técnico**, como la monitorización avanzada y la mejora de la comunicación LoRa, que hacen que el proyecto resulte especialmente completo y sorprendente. Todo ello se presenta de forma cuidada tanto en el repositorio de GitHub como en el **vídeo demostrativo**, que muestra de manera clara y profesional el funcionamiento del sistema.

## 🧪 Video demostración

