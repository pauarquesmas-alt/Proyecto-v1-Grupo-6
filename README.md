Proyecto Grupo 6
🌍 Descripción general
<p align="justify"> Este proyecto implementa un prototipo de **sistema satelital** formado por dos Arduinos: un **satélite** (controlador) y una **estación de tierra**. El satélite capta datos con distintos sensores, los procesa y los envía periódicamente. La estación de tierra recibe esa telemetría, la valida y la muestra en una **interfaz gráfica en Python**, desde donde también se pueden enviar comandos para controlar el satélite. Con cada versión se añaden nuevas funciones para acercar el sistema a una misión real. </p>
Versión 1
📋 Descripción
<p align="justify"> Primera versión funcional del sistema. El satélite mide **temperatura y humedad (DHT11)** y envía los datos por serie. La estación de tierra los recibe y los representa en una **gráfica dinámica en Python**. </p>
🧪 Video demostración

https://youtu.be/FFqi9oINteE

Versión 2
📋 Descripción
<p align="justify"> Se añade el **radar ultrasónico (HC-SR04)** y un **servo** para orientarlo. La interfaz en Python muestra T/H, **media móvil**, radar semicircular y permite cambiar periodos, activar barrido y lanzar alarmas por límite o fallo de sensores. </p>
🧪 Video demostración

https://youtu.be/GcaQ2BR3xfE?si=nUMKSqZa3t8V-v8U

Versión 3
📋 Descripción
<p align="justify"> Se incorpora la **simulación orbital** (envío de X,Y,Z) con gráfica 2D en tierra, comunicación **LoRa bidireccional**, checksum, filtrado por grupo y **registro de eventos**. También se detectan fallos de comunicación y se avisa con alarma. </p>
🧪 Video demostración

