# Changelog

Todos los cambios notables de este proyecto se documentarán en este archivo.

## [Unreleased] - 2026-07-09

### Add
* **Automatización del entorno:** scripts de arranque `ini.ps1` (Windows)e `ini.sh` (Linux/macOS) para crear el entorno virtual e instalar dependencias.
* **Ingesta de datos:** `01_descarga.py`, primer paso del pipeline. Descarga los datasets públicos vía API CKAN del portal de datos abiertos de Madrid, con reintentos ante bloqueos anti-bot, idempotencia y registro de metadatos de procedencia y licencia.
* **Configuración y dependencias:** `config.py` (catálogos, años, magnitudes y reglas de filtrado por conjunto) y `requirements.txt`.

### Notes
* Este es el primer registro del changelog. El historial previo (~30 commits) corresponde a la redacción de la memoria en LaTeX bajo `master's thesis/` (plantilla TeXiS, capítulos, apéndices, bibliografía... Mayormente estado de la cuestion e investigacion) y no está desglosado aquí por ser anterior a la adopción de este archivo.