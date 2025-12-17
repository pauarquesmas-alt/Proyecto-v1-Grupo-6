
<h1 align="center">🛰️ Estación Satélite Arduino</h1>

<p align="center">
Sistema de telemetría con Arduino y visualización en tiempo real en Python
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Estado-Activo-success">
  <img src="https://img.shields.io/badge/Arduino-UNO-blue">
  <img src="https://img.shields.io/badge/Python-3.10-yellow">
  <img src="https://img.shields.io/badge/Comunicación-LoRa-blueviolet">
</p>

<h2>👥 El equipo</h2>

<ul>
  <li><strong>Giulia Latorre Magliocco</strong></li>
  <li><strong>Pau Arques Mas</strong></li>
  <li><strong>Aina Sambró Gómez</strong></li>
</ul>

<hr>

<h2 align="center">VERSIÓN 1</h2>

<h2>📄 Descripción</h2>

<p>
Proyecto que conecta un Arduino <strong>controlador (satélite)</strong> con un Arduino
<strong>estación de tierra</strong> mediante comunicación serie.
</p>

<p>
El satélite mide <strong>temperatura y humedad</strong>, envía los datos en tiempo real y la
estación de tierra los recibe, procesa y muestra en una
<strong>gráfica dinámica desarrollada en Python</strong>.
</p>

<h2>🎥 Video demostración</h2>

👉 https://youtu.be/FFqi9oINteE

<blockquote>
Se recomienda visualizar el video para observar la transmisión y el graficado en tiempo real.
</blockquote>


## 🧠 Arquitectura del sistema

```text
[ Sensor DHT ]
      ↓
[ Arduino Satélite ]
      ↓  Comunicación Serie
[ Arduino Estación de Tierra ]
      ↓  USB
[ Interfaz Python ]
```

<hr>
<h2 align="center">VERSIÓN 2</h2>

<h2>📄 Descripción</h2>

<p>
El proyecto implementa una estación de tierra conectada a un “satélite” Arduino que mide temperatura, humedad y distancia con ultrasonidos. Desde el ordenador, una interfaz en Python muestra en tiempo real las gráficas de T/H y la media móvil, controla el periodo de envío de datos y el movimiento del servo, dibuja un radar con la distancia detectada y lanza alarmas cuando las medias de temperatura superan un umbral o se detectan fallos en los sensores.
</p>

<h2>🎥 Video demostración</h2>

👉 https://youtu.be/GcaQ2BR3xfE?si=nUMKSqZa3t8V-v8U

<blockquote>
Se recomienda visualizar el vídeo para observar en tiempo real la transmisión de datos de temperatura, humedad y proximidad, así como su graficado dinámico y la interacción con el sistema mediante el envío de órdenes al satélite.
</blockquote>

## 🧠 Arquitectura del sistema

```text
[ Sensor DHT (Temp / Hum) ]        [ Sensor Ultrasonidos ]
             ↓                              ↓
        [ Arduino Satélite ] ── Control ── [ Servo motor ]
             ↓   ↑
     Comunicación Serie / LoRa
             ↓   ↑
   [ Arduino Estación de Tierra ]
             ↓
            USB
             ↓
     [ Interfaz Python (GUI) ]
      - Gráficas
      - Alarmas
      - Envío de órdenes
```


<hr>
<h2 align="center">VERSIÓN 3</h2>

<h2>📄 Descripción</h2>

<p>
Las novedades principales de la versión 3 son: un sistema de detección de errores en la comunicación, el envío por parte del satélite de datos sobre su posición que se mostrarán en una gráfica apropiada, la implementación de un sistema de comunicación inalámbrica entre el satélite y la estación de tierra y la implementación de un sistema de registro de eventos.
</p>

<h2>🎥 Video demostración</h2>

👉 https://youtu.be/kKIEUvKRv5c

<blockquote>
Se recomienda visualizar el video para observar la transmisión y el graficado en tiempo real.
</blockquote>
<hr>

<h2 align="center">VERSIÓN 4</h2>

<h2>📄 Descripción</h2>
<p align="justify">
La <strong>Versión 4</strong> introduce un conjunto de <strong>mejoras avanzadas</strong> que elevan el sistema a un nivel más profesional y completo. Entre las principales novedades destacan el <strong>rediseño integral de la interfaz gráfica de la estación de tierra</strong>, la incorporación de un <strong>sistema de inicio de sesión</strong> para controlar el acceso al satélite, una <strong>nueva pantalla de monitorización avanzada</strong> que muestra los últimos valores recibidos y la media de las diez últimas temperaturas, así como la <strong>optimización de las gráficas</strong>, limitadas a los valores más recientes para mejorar claridad y rendimiento. Además, se ha <strong>optimizado la comunicación LoRa</strong> para evitar la saturación del canal y garantizar una transmisión más estable y fiable. Todas estas mejoras se han implementado tras corregir e integrar las sugerencias recibidas en versiones anteriores.
</p>

<p align="justify">
La Versión 4 consolida así un sistema completo, estable y técnicamente maduro, en el que se integran todas las funcionalidades exigidas hasta la Versión 3 junto con estas nuevas aportaciones, siguiendo fielmente los criterios de evaluación definidos en la asignatura.
</p>

<p align="justify">
Desde el punto de vista funcional, el prototipo <strong>cumple íntegramente los requisitos especificados</strong>, implementando la captura, el procesamiento y la transmisión de datos de temperatura, humedad y posición del satélite. La comunicación bidireccional con la estación de tierra permite tanto el envío periódico de información como el control remoto del satélite, y su correcto funcionamiento ha sido verificado mediante pruebas integradas del sistema completo.
</p>

<p align="justify">
El diseño del sistema prioriza la <strong>robustez</strong>, permitiendo gestionar errores de sensores, posibles fallos en la comunicación y entradas incorrectas del usuario sin provocar bloqueos. De este modo, el sistema mantiene un comportamiento estable y predecible incluso ante situaciones anómalas, reforzando su fiabilidad.
</p>

<p align="justify">
La estación de tierra dispone de una <strong>interfaz gráfica clara e intuitiva</strong>, resultado del rediseño completo realizado en esta versión. La información se presenta de forma ordenada mediante pantallas de monitorización y gráficas optimizadas, mientras que el sistema de inicio de sesión aporta una capa adicional de control y profesionalización. La interacción con el usuario es sencilla y no genera ambigüedades.
</p>

<p align="justify">
El código del satélite y de la estación de tierra está <strong>bien organizado y documentado</strong>, estructurado en funciones claramente definidas y acompañado de comentarios explicativos. Esta organización facilita la comprensión del sistema y permite realizar modificaciones o ampliaciones con un esfuerzo reducido. Asimismo, se han utilizado algoritmos y estructuras de datos eficientes, optimizando el rendimiento, la visualización de la información y el uso del canal de comunicación.
</p>

<p align="justify">
Finalmente, la Versión 4 incorpora <strong>funcionalidades adicionales de alto valor técnico</strong>, como la monitorización avanzada y la mejora de la comunicación LoRa, que hacen que el proyecto resulte especialmente completo y sorprendente. Todo ello se presenta de forma cuidada tanto en el repositorio de GitHub como en el vídeo demostrativo, que muestra de manera clara y profesional el funcionamiento del sistema.
</p>

<p>
Las novedades principales de la versión 3 son: un sistema de detección de errores en la comunicación, el envío por parte del satélite de datos sobre su posición que se mostrarán en una gráfica apropiada, la implementación de un sistema de comunicación inalámbrica entre el satélite y la estación de tierra y la implementación de un sistema de registro de eventos.
</p>

<h2>🎥 Video demostración</h2>

👉 

<blockquote>
Se recomienda visualizar el video para observar la transmisión y el graficado en tiempo real.
</blockquote>
<hr>


