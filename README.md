# Soluciones cloud para el análisis de datos públicos con IA

Trabajo de Fin de Máster en Ingeniería Informática
Universidad Complutense de Madrid
Curso 2025-2026

**Autor:** Cristian Molina Muñoz
**Directores:** José Luis Vázquez-Poletti, Rubén Fuentes-Fernández


## Introducción

Este proyecto se basa en tres tecnologías. La computación en la nube, la cuál se entiende como el suministro de servicios informáticos (servidores, almacenamiento, bases de datos, redes, software, análisis y más) a través de Internet, permitiendo un acceso flexible y escalable a recursos sin la necesidad de poseer ni gestionar la infraestructura física. La segunda es la Inteligencia Artificial (IA), que abarca el desarrollo de sistemas que demuestran la capacidades (una o varias) de aprender, adaptarse, razonar y resolver problemas complejos, así como de percibir y comprender su entorno (virtual o físico), a menudo a través del análisis y la inferencia a partir de grandes volúmenes de datos (mediante la rama de la IA conocida como Aprendizaje Automático, ML por sus siglas en inglés). Finalmente, el procesamiento de los grandes volúmenes de datos, que se refieren a colecciones masivas y heterogéneas de información generada o recopilada por entidades gubernamentales u organizaciones, accesible al público. 
El proyecto estudia la manera en la que estas tres tecnologías se pueden combinar para aportar un valor tangible.

## Contenido

Un pipeline reproducible que descarga datos abiertos del Ayuntamiento de Madrid, los limpia y los analiza con técnicas de aprendizaje no supervisado, ejecutable sin cambios en tres entornos: local, AWS y Google Cloud Platform. 
El coste neto de ejecutarlo en la nube es cubierto por las capas gratuitas.

El caso de estudio es la isla de calor de Madrid. Se replica el Trabajo de Fin de Grado [«Madrid, isla de calor»](https://hdl.handle.net/20.500.14352/3348) (Meneses Vicente y García Ruiz, 2023), que analizaba un único año, y se extiende la serie de 2019 a 2025 añadiendo dos aproximaciones propias y un criterio de cobertura mínima por estación. 
También se procesaron los datos de movilidad de [«Análisis de datos de la ciudad de Madrid»](https://hdl.handle.net/20.500.14352/88404) (Saiz Santos, 2023), aunque su análisis quedó fuera de alcance.

Al automatizar la ingesta sobre siete años aparecieron problemas de calidad que un estudio de un solo año no detecta: cambios de nomenclatura y de unidades sin documentar, esquemas que mutan a mitad de serie y degradación de la red de sensores. Ese hallazgo es una de las aportaciones del trabajo.

## Cómo ejecutarlo

Requiere Python 3.12 o superior.

```bash
git clone https://github.com/crismo04/TFM-cloud-soliutions-to-public-data.git
cd TFM-cloud-soliutions-to-public-data/code/files

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

python 01_descarga.py --dry-run    # comprueba los enlaces sin descargar
python 01_descarga.py
python 02_limpieza.py
python 03_analisis_isla_calor.py
```

Los detalles para todas las nubes y entornos se describen en la capitulo 5 de la memoria en PDF adjuntada en este repositorio.

## Datos y licencias

Los conjuntos proceden del [Portal de Datos Abiertos del Ayuntamiento de Madrid](https://datos.madrid.es/) bajo licencia CC BY 4.0: calidad del aire, meteorología, masas arbóreas por distrito, aforos de peatones y bicicletas, estaciones de control y el shapefile de distritos.

Los datos descargados no se versionan aquí por superar los 100 MB, pero sí los resultados, para permitir contrastar las tablas y figuras de la memoria. La procedencia de cada fichero queda registrada en `data/bronze/_metadatos.csv`.

## Memoria

El PDF completo está en `master's thesis/`. El historial de cambios, en [CHANGELOG.md](CHANGELOG.md).