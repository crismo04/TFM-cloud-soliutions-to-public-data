# Changelog

Todos los cambios notables de este proyecto se documentarán en este archivo, el mas reciente primero.

## [Cloud] - 2026-08-19
### Add
* Modificacion de la memoria de tabla de tiempos
### Change
* Adaptacion del python de limpieza para poder ejecutar en glue
* Otros cambios menores

## [Thesis] - 2026-08-16
### Add
* Añadido la parte del capítulo 5, que habla sobre cómo utilizar la solución, para explicar cómo se ha creado la cuenta de Amazon web Services. 
* Toda la parte del capitulo 5 que indica como utilizar la solucion en AWS hasta la descarga
* Añadido apéndice B para comentar cuál han sido los usos de inteligencia artificial.
### Change
* Pequeñas mejoras en la memoria
* Mejoras para poder ver el codigo en la memoria
* Otros cambios relacionados con AWS en el capitulo 3 y 4 

## [Data] - 2026-07-29
### Change
* Actualizacion del PDF y añadida la carpeta de resultados por trazabilidad y seguir el compromiso de codigo abierto y datos (datos no publicados por exceder los 100MB)


## [ML] - 2026-07-27
### Change
* Viendo el TFM isla de calor he visto que habia un analsis que estaba haciendo con los parametros incorrectos (para la replica), cambiado
* Añadido un modo para poder meter la configuracion de replica vs mejora para facilitar el analisis
* Estudio de los datos obtenidos y escritura del capitulo 3 y 4 sobre los mismos
* Mas mejoras que he ido viendo en el proceso 3 (isla de calor)

## [ML] - 2026-07-18
### Add
* **Primer tratamiento de datos :** `03_analisis_isla_calor.py`, tercer paso del pipeline, modelado, centrandonos en el TFM de "madrid isla de calor". 
* **Memoria:** Actualización de los ficheros de LaTeX del capítulo 3: Documentacion del pipeline analítico (arquitectura, limpieza de datos y modelos espaciales de IA) diseñado para replicar y extender el estudio de la isla de calor.
* Actualización de la **biografía** con las referencias a estos avances.
### Change
* Reestructuracion de los ficheros de LaTeX del capítulo 3: Ahora el orden es Materiales, metodos y utilizacion.
* Revision de los materiales utiulizados y simplificacion de algunas definiciones antiguas.


## [Data] - 2026-07-12
### Add
* **Memoria:** Actualización de los ficheros de LaTeX del capítulo 3, en la parte de datos realizada en el commit anterior. Actualización de la biografía con las referencias a estos avances
* **Limpieza de datos:** `02_limpieza.py`, segundo paso del pipeline. Limpia los datos descargados dependiendo del tipo de archivo
### Change
* Correcciones menores de redaccion en los ficheros latex
* Nuevas reglas de limpieza en config


## [Data] - 2026-07-09
### Add
* **Automatización del entorno:** scripts de arranque `ini.ps1` (Windows)e `ini.sh` (Linux/macOS) para crear el entorno virtual e instalar dependencias.
* **Ingesta de datos:** `01_descarga.py`, primer paso del pipeline. Descarga los datasets públicos vía API CKAN del portal de datos abiertos de Madrid, con reintentos ante bloqueos anti-bot, idempotencia y registro de metadatos de procedencia y licencia.
* **Configuración y dependencias:** `config.py` (catálogos, años, magnitudes y reglas de filtrado por conjunto) y `requirements.txt`.


## First commmit notes
* Este es el primer registro del changelog. El historial previo (~30 commits) corresponde a la redacción de la memoria en LaTeX bajo `master's thesis/` (plantilla TeXiS, capítulos, apéndices, bibliografía... Mayormente estado de la cuestion e investigacion) y no está desglosado aquí por ser anterior a la adopción de este archivo.