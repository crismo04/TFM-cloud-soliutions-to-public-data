"""
Limpieza y normalizacion de los datos descargados

Cada conjunto tiene un tipo de limpieza declarado en config.LIMPIEZA, de forma que anadir un conjunto nuevo solo requiere una nueva linea alli.
Los cuatro tipos:
  mensual_dv :
    replica la logica de limpieza.R del TFG "Madrid, isla de calor": valor valido solo si V## == 'V' (si no, NaN) y fechas imposibles (30-feb, 31-sep...) descartadas.
    Origen (una fila = estacion x magnitud x mes con columnas D01/V01..D31/V31)
    Destino (una fila = estacion x dia, una columna por magnitud)
    Reglas identicas al TFG

  aforos:
    consolida los ficheros anuales en un unico fichero largo (similar a la preparacion del TFG de peatones: los datos solo requieren union, fechas y tipado).

  tabla_anual:
    tablas pequeñas publicadas por año (arbolado), unidas añadiendo la columna 'anio' extraida del nombre del fichero.

  directo:
    ficheros unicos (estaciones), se normalizan columnas y copian.

Uso:
  python 02_limpieza.py                         # config.LIMPIEZA completa
  python 02_limpieza.py peatones meteo_diario   # un unico registro
"""
from __future__ import annotations

import os, sys
import re
import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

if "--TFM_BASE" in sys.argv:
    os.environ["TFM_BASE"] = sys.argv[sys.argv.index("--TFM_BASE") + 1]
import config


# --- utilidades comunes --

def _sin_tildes(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()

def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [_sin_tildes(c).strip().upper().replace(" ", "_")
                  for c in df.columns]
    return df

def _leer_csv_flexible(ruta: str) -> pd.DataFrame:
    """Los ficheros del Ayuntamiento usan ';' y codificaciones variadas""" # TODO cambiar para mas codificaciones en diferentes fuentes
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(ruta, sep=";", encoding=enc, dtype=str)
            if df.shape[1] > 1:
                return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"No se pudo leer {ruta}")

def _sort_csv_list(clave: str) -> list[str]:
    """Busca los archivos en las carpetas y subcarpetas y devuelve una lista ordenada"""
    import fsspec
    carpeta = f"{config.BRONZE}/{clave}"
    fs, ruta = fsspec.core.url_to_fs(carpeta)
    if not fs.exists(ruta):
        return []
    proto = "s3://" if str(config.BRONZE).startswith("s3://") else ""
    return sorted(proto + f for f in fs.find(ruta)
                  if f.endswith(".csv") and not f.split("/")[-1].startswith("_"))

def _parse_fechas(serie: pd.Series) -> pd.Series:
    """El formato de fecha cambia entre ficheros. Se detecta por patron:
    - si empieza por el año (yyyy-...) es ISO; si no, formato español con dia primero.
     WARNING -> dayfirst=True sobre fechas ISO intercambia mes y dia"""
    s = serie.astype(str).str.strip()
    muestra = next((v for v in s if v and v.lower() not in ("nan", "nat")), "")
    es_iso = bool(re.match(r"^\d{4}[-/]", muestra))
    return pd.to_datetime(s, errors="coerce", dayfirst=not es_iso)

def _convertir_decimales(df: pd.DataFrame) -> pd.DataFrame:
    """Numeros del portal con coma decimal ('123456,00')"""
    for col in df.columns:
        if not pd.api.types.is_string_dtype(df[col]):
            continue
        s = df[col]
        con_coma = s.str.contains(",", na=False)
        s = s.where(~con_coma, s.str.replace(".", "", regex=False))
        num = pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")

        # Comprobamos que al menos el 90% se ha podido convertir
        if num.notna().any() and num.notna().sum() >= df[col].notna().sum() * 0.9:
            df[col] = num
    return df

def _guardar(df: pd.DataFrame, nombre: str) -> None:
    """Escribe silver en parquet si hay motor disponible; siempre en csv"""
    salida = f"{config.SILVER}/{nombre}"
    if not str(config.SILVER).startswith("s3://"):
        Path(config.SILVER).mkdir(parents=True, exist_ok=True)
    df.to_csv(f"{salida}.csv", index=False)
    try:
        df.to_parquet(f"{salida}.parquet", index=False)
    except ImportError:
        print("  [aviso] sin parquet, solo csv")



# --- tipo mensual_dv (mes a dias validados)--
#  1 fila por mes con columnas D01/V01 hasta D31/V31 -> modelo diario.

def _mensual_a_diario(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma el formato ancho mensual del portal a largo diario (un pivot vamos para los datos de dias)"""
    df = _normalizar_columnas(df)
    registros = []
    for d in range(1, 32):
        col_dato, col_valid = f"D{d:02d}", f"V{d:02d}"
        if col_dato not in df.columns:
            continue
        sub = df[["ESTACION", "MAGNITUD", "ANO", "MES"]].copy()
        sub["valor"] = pd.to_numeric(df[col_dato].astype(str).str.replace(",", "."), errors="coerce")

        # solo valores verificados por el portal ('V'), el resto, Nan
        if col_valid in df.columns:
            sub.loc[df[col_valid].astype(str).str.upper() != "V", "valor"] = np.nan
        sub["dia"] = d
        registros.append(sub)
    largo = pd.concat(registros, ignore_index=True)

    # Saneamiento de fechas con pandas
    largo["fecha"] = pd.to_datetime(
        dict(year=pd.to_numeric(largo["ANO"], errors="coerce"),
             month=pd.to_numeric(largo["MES"], errors="coerce"),
             day=largo["dia"]),
        errors="coerce")
    largo = largo.dropna(subset=["fecha"])
    largo["ESTACION"] = pd.to_numeric(largo["ESTACION"], errors="coerce")
    largo["MAGNITUD"] = pd.to_numeric(largo["MAGNITUD"], errors="coerce")
    return largo[["ESTACION", "MAGNITUD", "fecha", "valor"]]


def limpiar_mensual_dv(clave: str, magnitudes: dict[int, str]) -> None:
    """limpia ficheros mensual_dv, unifica los CSVs, recorta los años fuera de config.ANIOS, mapea magnitud
    y pivota el resultado a series temporales (Estación, Fecha, Magnitud 1, Magnitud 2...)."""
    partes = []
    for ruta in _sort_csv_list(clave):
        nombre = ruta.split("/")[-1]
        try:
            df = _leer_csv_flexible(ruta)
            if "MES" in [_sin_tildes(c).strip().upper() for c in df.columns]:
                partes.append(_mensual_a_diario(df))
                print(f"  [ok  ] {nombre}")
        except Exception as e:  # noqa: BLE001 - log y seguir
            print(f"  [fail] {nombre}: {e}")
    if not partes:
        print(f"  [AVISO] '{clave}' sin ficheros mensuales procesables")
        return
    largo = pd.concat(partes, ignore_index=True)

    # El Ayuntamiento a veces incluye datos de 2026 en el histórico
    fuera = ~largo["fecha"].dt.year.isin(config.ANIOS)
    if fuera.any():
        print(f"  [info] descartadas {fuera.sum()} filas fuera de ANIOS")
        largo = largo[~fuera]
    largo = largo[largo["MAGNITUD"].isin(magnitudes)] # mapeo a magnitudes legibles
    largo["magnitud"] = largo["MAGNITUD"].map(magnitudes)

    # Pivot para crear la tabla final
    ancho = (largo.pivot_table(index=["ESTACION", "fecha"], columns="magnitud",
                               values="valor", aggfunc="mean")
                  .reset_index()
                  .rename(columns={"ESTACION": "estacion"}))
    _guardar(ancho, f"{clave}_diario")
    n_nan = ancho.drop(columns=["estacion", "fecha"]).isna().mean().mean()
    print(f"  -> {clave}_diario: {len(ancho)} filas, "
          f"{ancho['estacion'].nunique()} estaciones, {n_nan:.1%} NaN medio")


# --- tipo aforos (conteos anuales) --
# Archivos sueltos (Excel/CSV) que requieren unificación vertical (append).

def limpiar_aforos(clave: str, columnas_valor: list[str]) -> None:
    """Unifica archivos de aforos (peatones/bicis), estandariza la columna de conteo,
    tipa las fechas/horas y filtra por el rango de años configurado."""
    partes, col_valor = [], None
    # Ingesta para csvs
    ficheros = _sort_csv_list(clave)
    for ruta in ficheros:
        nombre = ruta.split("/")[-1]
        try:
            df = _leer_csv_flexible(ruta)
            df = _normalizar_columnas(df)
            # el esquema cambio a mitad de serie:
            # columnas renombradas, en ingles, erroes (NAOMERO)... unificadas
            df = df.rename(columns={
                "DIRECCION": "NOMBRE_VIAL",
                "LATITUDE": "LATITUD",
                "LONGITUDE": "LONGITUD",
                "NAOMERO_DISTRITO": "NUMERO_DISTRITO",
            })
            col = next((c for c in columnas_valor if c in df.columns), None)
            if col is None:
                print(f"  [skip] {nombre}: sin columna de conteo esperada")
                continue
            col_valor = col_valor or col
            df = df.rename(columns={col: col_valor})
            # la fecha se parsea por fichero: el formato cambia entre años # TODO ????
            df["FECHA"] = _parse_fechas(df["FECHA"])
            rango = (f"{df['FECHA'].min():%Y-%m-%d} a {df['FECHA'].max():%Y-%m-%d}"
                     if df["FECHA"].notna().any() else "sin fechas validas")
            partes.append(df)
            print(f"  [ok  ] {nombre}: {len(df)} filas ({rango})")
        except Exception as e:  # noqa: BLE001
            print(f"  [fail] {nombre}: {e}")
    if not partes:
        print(f"  [AVISO] '{clave}' sin ficheros de aforos que se puedan leer")
        return
    total = pd.concat(partes, ignore_index=True)

    # limpiamos
    total[col_valor] = pd.to_numeric(total[col_valor], errors="coerce")
    if "HORA" in total.columns:  # puede venir como '12:00' o datetime.time
        total["HORA_NUM"] = (total["HORA"].astype(str)
                             .str.extract(r"(\d{1,2})")[0].astype(float))
    total = total.dropna(subset=["FECHA", col_valor])
    total = total[total["FECHA"].dt.year.isin(config.ANIOS)]
    total = total.drop_duplicates()
    total = _convertir_decimales(total)
    _guardar(total, f"{clave}_total")
    print(f"  -> {clave}_total: {len(total)} filas, "
          f"{total['FECHA'].min():%Y-%m-%d} a {total['FECHA'].max():%Y-%m-%d}")


# --- tipo tabla_anual (con el año en el nombre del fichero) --

def _quitar_filas_basura(df: pd.DataFrame) -> pd.DataFrame:
    """El portal incrusta en el propio csv filas vacias, de totales y notas al pie ?? TODO documentar en memoria"""
    datos = df.drop(columns=["ANIO"], errors="ignore")
    casi_vacias = datos.notna().mean(axis=1) < 0.35
    texto = datos.fillna("").astype(str).apply(" ".join, axis=1).str.upper()
    basura = casi_vacias | texto.str.contains("NOTA") | texto.str.contains("TOTALES")
    return df[~basura]

def limpiar_tabla_anual(clave: str, _param) -> None:
    """Extrae el año del nombre del fichero con Regexp y lo añade como columna"""
    partes = []
    for ruta in _sort_csv_list(clave):
        nombre = ruta.split("/")[-1]
        try:
            df = _normalizar_columnas(_leer_csv_flexible(ruta))
            m = re.match(r"^(20\d{2})_", nombre)
            df["ANIO"] = int(m.group(1)) if m else pd.NA
            df = _quitar_filas_basura(df)
            partes.append(df)
            print(f"  [ok  ] {nombre}: {len(df)} filas")
        except Exception as e:  # noqa: BLE001
            print(f"  [fail] {nombre}: {e}")
    if not partes:
        print(f"  [AVISO] '{clave}' sin tablas anuales procesables")
        return

    # Schema Evolution: si el esquema cambia en un año concreto (como paso 2024),
    # pd.concat alinea las cabeceras y rellena los huecos con NaN  # TODO revisar la salida
    total = _convertir_decimales(pd.concat(partes, ignore_index=True))
    _guardar(total, f"{clave}_anual")
    cols = [c for c in total.columns if c != "ANIO"]
    print(f"  -> {clave}_anual: {len(total)} filas, "
          f"anios {sorted(total['ANIO'].dropna().unique())}, "
          f"{len(cols)} columnas")


# --- tipo directo (maestros/dimensiones) --
# Tablas de búsqueda o dimensiones como el listado de estaciones

def limpiar_directo(clave: str, _param) -> None:
    """Lee y guarda sin transformaciones extra"""
    for ruta in _sort_csv_list(clave):
        nombre = ruta.split("/")[-1]
        try:
            df = _normalizar_columnas(_leer_csv_flexible(ruta))
            # las coordenadas de las estaciones vienen con coma decimal
            df = _convertir_decimales(df)
            _guardar(df, clave)
            print(f"  [ok  ] {nombre} -> {clave}: "
                  f"{len(df)} filas, {len(df.columns)} columnas")
        except Exception as e:  # noqa: BLE001
            print(f"  [fail] {nombre}: {e}")


# --- principal --

TIPOS = {
    "mensual_dv": limpiar_mensual_dv,
    "aforos": limpiar_aforos,
    "tabla_anual": limpiar_tabla_anual,
    "directo": limpiar_directo,
}

def _claves_desde_argv() -> list[str]:
    """Argumentos declarados en la configuracion, 
    porque la nube inyecta sus propios parametros al invocar el proceso"""
    return [a for a in sys.argv[1:] if a in config.LIMPIEZA]

def main() -> None:
    claves = _claves_desde_argv() or list(config.LIMPIEZA)
    for clave in claves:
        tipo, param = config.LIMPIEZA[clave]
        print(f"== {clave} ({tipo}) ==")
        TIPOS[tipo](clave, param)

if __name__ == "__main__":
    main()