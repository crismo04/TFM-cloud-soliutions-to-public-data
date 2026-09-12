# Changelog

Todos los cambios notables de este proyecto se documentarán en este archivo, el más reciente primero.


## [CORRECCIONES POST ENVÍO, SOLO MEMORIA] - 2026-09-12
### Change
* Correcciones de algunos enlaces dañados.
* Los enlaces clicables de la introducción, en cursiva.
* Cambio en algunos títulos de sección por repetitivos.
* Mejoras de redacción propuestas por los tutores.
* Correcciones ortográficas (incluido este changelog).
* Se redirige a la definición de arquitectura de medalla en el capítulo de estado de la cuestión.
* Se ajustaron todas las tablas al margen de la memoria.
* Se ajustaron las imágenes.
* Se enumeraron también los capítulos de las conclusiones de cada capítulo.
* En el manual de usuario, los bloques de código estaban mal organizados, no se colocaban después de los dos puntos. Se ha cambiado la manera de introducirlos en los párrafos.
* Añadido un apartado de conclusiones del capítulo en el manual de usuario.
* Corregidas dos medias desactualizadas en las siluetas del capítulo 4
* Añadido un apartado de marco metodológico en la sección 3.2
* Actualizacion de los readme.md del codigo


## [VERSIÓN DEL TRIBUNAL] - 2026-09-04
### Change
* Asociar bloques de código en el capítulo 5 y recompilar, PDF revisado.


## [Memoria] - 2026-09-03
### Change
* Revisión de los tutores aplicada a la memoria, final de conclusiones.
* Retoques de estilo y actualización de acrónimos.


## [Memoria] - 2026-09-02
### Add
* Toques finales del capítulo 4 de la memoria.
### Change
* Modificaciones menores en la memoria de estilo y correcciones.


## [Memoria] - 2026-09-01
### Add
* Toques finales de los capítulos 2 y 3 de la memoria.
### Change
* Modificaciones menores en la memoria de estilo y correcciones.


## [ML] - 2026-08-31
### Add
* Añadir dos nuevas aproximaciones: (Temperatura y altitud) y (Temperatura y superficie relativa).
* Nuevos resultados debido a las nuevas aproximaciones.
### Change
* Modificaciones menores en la memoria.
* Dejar los códigos 01, 02 y 03 funcionando y sin TODOs en todas las plataformas.


## [Cloud] - 2026-08-27
### Change
* WIP de parte de GCP en la memoria.
* Organizar TODOs del capítulo 4.
* Revisión general de TODOs en la memoria.
* Reestructuración del manual de usuario.


## [Cloud] - 2026-08-25
### Add
* Nuevo archivo de Jupyter Notebooks para ejecutar el análisis 3.
* Inicio de la parte de GCP.
* Nueva parte del manual de usuario para la creación y uso de SageMaker.
* Añadidas las fotos para acompañar las explicaciones del manual de usuario.
### Change
* Reestructuración de la última parte del manual de usuario.
* Mejora en los gráficos poniendo el nombre de las estaciones.
* Otras correcciones menores de la memoria.
### Fix
* Corrección del proceso 3 para su ejecución en SageMaker.
* Corrección de diversas erratas en la memoria y cambios menores.


## [Cloud] - 2026-08-23
### Add
* Modificación de la memoria con AI Act y correcciones.
* Nueva parte del manual de usuario para la creación y uso de Glue en AWS.
### Fix
* Corrección de más problemas que surgieron en AWS.


## [Cloud] - 2026-08-19
### Add
* Modificación de la memoria de tabla de tiempos.
### Change
* Adaptación del Python de limpieza para poder ejecutar en Glue.
* Otros cambios menores.


## [Thesis] - 2026-08-16
### Add
* Añadida la parte del capítulo 5, que habla sobre cómo utilizar la solución, para explicar cómo se ha creado la cuenta de Amazon Web Services.
* Toda la parte del capítulo 5 que indica cómo utilizar la solución en AWS hasta la descarga.
* Añadido apéndice B para comentar cuáles han sido los usos de inteligencia artificial.
### Change
* Pequeñas mejoras en la memoria.
* Mejoras para poder ver el código en la memoria.
* Otros cambios relacionados con AWS en los capítulos 3 y 4.


## [Data] - 2026-07-29
### Change
* Actualización del PDF y añadida la carpeta de resultados por trazabilidad y para seguir el compromiso de código abierto y datos (datos no publicados por exceder los 100 MB).


## [ML] - 2026-07-27
### Change
* Viendo el TFG "Madrid, isla de calor" he visto que había un análisis que estaba haciendo con los parámetros incorrectos (para la réplica), cambiado.
* Añadido un modo para poder meter la configuración de réplica vs. mejora para facilitar el análisis.
* Estudio de los datos obtenidos y escritura de los capítulos 3 y 4 sobre los mismos.
* Más mejoras que he ido viendo en el proceso 3 (isla de calor).


## [ML] - 2026-07-18
### Add
* **Primer tratamiento de datos:** `03_analisis_isla_calor.py`, tercer paso del pipeline, modelado, centrándonos en el trabajo de "Madrid, isla de calor".
* **Memoria:** actualización de los ficheros de LaTeX del capítulo 3: documentación del pipeline analítico (arquitectura, limpieza de datos y modelos espaciales de IA) diseñado para replicar y extender el estudio de la isla de calor.
* Actualización de la **bibliografía** con las referencias a estos avances.
### Change
* Reestructuración de los ficheros de LaTeX del capítulo 3: ahora el orden es Materiales, Métodos y Utilización.
* Revisión de los materiales utilizados y simplificación de algunas definiciones antiguas.


## [Data] - 2026-07-12
### Add
* **Memoria:** actualización de los ficheros de LaTeX del capítulo 3, en la parte de datos realizada en el commit anterior. Actualización de la bibliografía con las referencias a estos avances.
* **Limpieza de datos:** `02_limpieza.py`, segundo paso del pipeline. Limpia los datos descargados dependiendo del tipo de archivo.
### Change
* Correcciones menores de redacción en los ficheros LaTeX.
* Nuevas reglas de limpieza en config.


## [Data] - 2026-07-09
### Add
* **Automatización del entorno:** scripts de arranque `ini.ps1` (Windows) e `ini.sh` (Linux/macOS) para crear el entorno virtual e instalar dependencias.
* **Ingesta de datos:** `01_descarga.py`, primer paso del pipeline. Descarga los datasets públicos vía API CKAN del portal de datos abiertos de Madrid, con reintentos ante bloqueos anti-bot, idempotencia y registro de metadatos de procedencia y licencia.
* **Configuración y dependencias:** `config.py` (catálogos, años, magnitudes y reglas de filtrado por conjunto) y `requirements.txt`.


## Primer commit
* Este es el primer registro del changelog. El historial previo (~30 commits) corresponde a la redacción de la memoria en LaTeX bajo `master's thesis/` (plantilla TeXiS, capítulos, apéndices, bibliografía... mayormente estado de la cuestión e investigación) y no está desglosado aquí por ser anterior a la adopción de este archivo. Fue desarrollado durante el curso académico 2024-2025.