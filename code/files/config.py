"""
Configuración central de la fase local en Python.

Los conjuntos se descargan a partir de las PÁGINAS DE CATÁLOGO del portal de datos abiertos, no de URLs directas a ficheros: 
    Los identificadores numéricos de cada fichero cambian cuando el Ayuntamiento republica...
    El codigo de 01_descarga.py parsea el HTML del catálogo y extrae los enlaces vigentes. 
    Si el portal cambia de estructura, solo hay que actualizar aquí.

"""

from pathlib import Path
import os

# direcciones de una arquitectura de medallon estandar
BASE = os.environ.get("TFM_BASE", str(Path(__file__).resolve().parent))
BRONZE = f"{BASE}/data/bronze"      # crudo, tal cual se descarga
SILVER = f"{BASE}/data/silver"      # limpio, formato largo diario
GOLD = f"{BASE}/data/gold"          # agregados listos para modelos
RESULTADOS = f"{BASE}/resultados"

# --- Páginas de catálogo (verificadas Julio-2026) ------------------------- #TODO añadir mas si se queda corto
CATALOGOS = {

    #  TFG "Madrid, isla de calor" 
    "calidad_aire_diario": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=aecb88a7e2b73410VgnVCM2000000c205a0aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
    ),

    # Datos meteorologicos. Datos diarios DESDE 2019 (la red se creo en 2018, no existen datos municipales anteriores)
    "meteo_diario": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=8d7357cec5efa610VgnVCM1000001d4a900aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
        "&vgnextfmt=default"
    ),
    "estaciones_aire": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=9e42c176313eb410VgnVCM1000000b205a0aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
    ),
    "estaciones_meteo": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=2ac5be53b4d2b610VgnVCM2000001f4a900aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
        "&vgnextfmt=default"
    ),

    # "Arbolado en parques y zonas verdes" - ficheros de masas arboreas
    # sin datos 2018 y cambio de esquema en ene-2024
    "arbolado_masas": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=0101507f09436610VgnVCM2000001f4a900aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
        "&vgnextfmt=default"
    ),

    # TFG "Analisis de datos de la ciudad de Madrid" (peatones)
    "peatones": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=695cd64d6f9b9610VgnVCM1000001d4a900aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
        "&vgnextfmt=default"
    ),
    "distritos": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=7d6e5eb0d73a7710VgnVCM2000001f4a900aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
        "&vgnextfmt=default"
    ),
    
    # Aforos de bicicletas: mismo paquete que peatones, subserie distinta. Ampliacion
    "bicicletas": (
        "https://datos.madrid.es/portal/site/egob/"
        "menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/"
        "?vgnextoid=695cd64d6f9b9610VgnVCM1000001d4a900aRCRD"
        "&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD"
        "&vgnextfmt=default"
    ),
    # TODO revisar los items y chanel, ver si añadir aqui las bicicletas
}

# Años a descargar. 2021 replica el TFG de isla de calor; 2019-2021 el de peatones
ANIOS = list(range(2019, 2026))  # meteo solo existe desde 2019

# Diccionarios de magnitudes del intérprete oficial del portal # TODO añadir a bib
MAGNITUDES_METEO = {
    80: "uv", 81: "vel_viento", 82: "dir_viento", 83: "temperatura",
    86: "humedad_rel", 87: "presion", 88: "rad_solar", 89: "precipitacion",
}
MAGNITUDES_CONTAMINACION = {
    1: "so2", 6: "co", 7: "no", 8: "no2", 9: "pm25", 10: "pm10",
    12: "nox", 14: "o3",
}

# Parámetros del análisis de peatones "Analisis de datos de la ciudad de Madrid"
PEATONES_CALLE = "GENOVA"   # se busca como subcadena, sin tildes  # TODO añadir mas calles?
PEATONES_HORA = 12
PEATONES_HORIZONTE_TEST = 15  # días reservados para validar el forecast

# --- Parámetros del análisis (03_analisis_isla_calor.py) ---
# MODO_REPLICA: True reproduce el TFG original tal cual - False activa las mejoras metodologicas propias
# MODO_REPLICA = True
MODO_REPLICA = False
ETIQUETA_MODO = "replica" if MODO_REPLICA else "propio"
MIN_DIAS_ANIO = 0 if MODO_REPLICA else 300  # dias validos minimos por estacion-año

# --- Reglas de Filtrado (Limpieza en origen) ---
# Evita descargar duplicados del mismo dataset en CSV y Excel o formatos innecesarios, si vacio, descarga todo
FORMATOS_POR_CONJUNTO = {
    "calidad_aire_diario": {"csv", "zip"},
    "meteo_diario": {"csv", "zip"},
    "estaciones_aire": {"csv"},
    "estaciones_meteo": {"csv"},
    "arbolado_masas": {"csv"},
    "peatones": {"csv"},
    "bicicletas": {"csv"},
    "distritos": {"zip"},
}

# Regex opcional (se aplica en minusculas y sin tildes sobre nombre+descripcion del recurso) para conjuntos con muchas subseries
# Arbolado publica 3 subseries x 2 ambitos: solo queremos las masas arboreas por distrito, que es lo que usa el TFG de isla de calor.
FILTROS_RECURSO = {
    "arbolado_masas": r"masas.*distrito",
    "peatones": r"aforos peatones",         # excluye "Aforos bicicletas"
    "bicicletas": r"aforos bicicletas",     # excluye "Aforos peatones"
    "distritos": r"distritos municipales",  # excluye divisiones historicas
}

# --- Reglas 02_limpieza.py ---
#   mensual_dv : formato D01/V01..D31/V31 del portal -> diario por estacion
#   aforos     : consolidar ficheros anuales de aforos (fecha + hora + conteo)
#   tabla_anual: tablas pequenas por anio (se anade columna 'anio' del nombre)
#   directo    : normalizar y copiar a silver tal cual (ficheros unicos)

LIMPIEZA = {
    "meteo_diario": ("mensual_dv", MAGNITUDES_METEO),
    "calidad_aire_diario": ("mensual_dv", MAGNITUDES_CONTAMINACION),
    "peatones": ("aforos", ["PEATONES"]),
    "bicicletas": ("aforos", ["BICICLETAS", "CICLISTAS", "BICIS"]),
    "arbolado_masas": ("tabla_anual", None),
    "estaciones_aire": ("directo", None),
    "estaciones_meteo": ("directo", None),
    # Los shapefile (distritos) no se limpian
}