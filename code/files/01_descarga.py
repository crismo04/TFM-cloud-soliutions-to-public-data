"""Descarga de datos crudos de diferentes portales publicos

El portal de datos abiertos de Madrid migro a CKAN (2.9.x), que expone la API REST estandar de CKAN. La estrategia de ingesta es por tanto:

  1. Resolver el package_id del conjunto: se acepta directamente el id o una URL antigua/nueva del catalogo (HTML -> window.packageId)
  2. Llamar a GET /api/3/action/package_show?id=<pkg> -> JSON con todos los recursos (url, nombre, formato) y la licencia del conjunto
  3. Filtrar recursos de datos (csv/xlsx/zip/json/shp...) por anio, que se detecta en el nombre/descripcion del recurso
  4. Descargar al destino elegido via fsspec y registrar metadatos

Uso:
  python 01_descarga.py --dry-run                        # solo listar
  python 01_descarga.py --destino data/bronze            # local (defecto)
  python 01_descarga.py --destino s3://bucket/bronze     # AWS (pip s3fs)
  python 01_descarga.py --destino gs://bucket/bronze     # GCP (pip gcsfs)
  python 01_descarga.py peatones meteo_diario            # solo algunos
"""

import argparse
import csv
import time
import io
import re
import sys
import zipfile
from datetime import datetime, timezone

import fsspec
import requests

import config

API_BASE = "https://datos.madrid.es/api/3/action"
PAUSA_ENTRE_DESCARGAS = 2.0   # dos segundo porque el portal usa proteccion anti-bot (Akamai)
REINTENTOS = 3
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/json,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}
SESION = requests.Session()
SESION.headers.update(HEADERS)

# Patrones de formato para lso paquetes en regexp
PATRON_PACKAGE = re.compile(r"window\.packageId\s*=\s*'([^']+)'")
PATRON_PACKAGE_ALT = re.compile(r'data-path="dataset/([^"]+)"')
FORMATOS_DATOS = {"csv", "xlsx", "xls", "zip", "json",
                  "shp", "geo", "geojson", "kml"}
PREFIJO_ID = re.compile(r"^\d{5,6}-\d{1,4}-")

def _normalizar(s: str) -> str:
    import unicodedata
    return (unicodedata.normalize("NFKD", s)
            .encode("ascii", "ignore").decode().lower())


# --- funciones para resolver recursos y paquetes --

def resolver_package_id(referencia: str) -> str | None:
    """Devuelve el package_id de CKAN a partir de un id directo o de una
    URL del catalogo (antigua estilo vgnextoid o nueva /dataset/...)"""
    if not referencia.startswith("http"):
        return referencia  # ya es un id
    m = re.search(r"/dataset/([^/?#]+)", referencia)
    if m:
        return m.group(1)
    html = SESION.get(referencia, timeout=60).text
    for patron in (PATRON_PACKAGE, PATRON_PACKAGE_ALT):
        m = patron.search(html)
        if m:
            return m.group(1)
    return None

def recursos_del_paquete(pkg: str) -> tuple[list[dict], str]:
    """Recursos de datos del paquete via API CKAN + licencia declarada"""
    r = SESION.get(f"{API_BASE}/package_show", params={"id": pkg}, timeout=60)
    r.raise_for_status()
    cuerpo = r.json()
    if not cuerpo.get("success"):
        raise RuntimeError(f"package_show fallo para {pkg}")
    paquete = cuerpo["result"]
    licencia = paquete.get("license_title") or paquete.get("license_id") or "?"
    recursos = []
    for rec in paquete.get("resources", []):
        formato = (rec.get("format") or "").strip().lower()
        url = rec.get("url") or ""
        if formato not in FORMATOS_DATOS:
            ext = url.rsplit(".", 1)[-1].lower() if "." in url else ""
            if ext not in FORMATOS_DATOS:
                continue  # para saltar documentacion (pdf) y otros
            formato = ext
        nombre = rec.get("name") or url.rsplit("/", 1)[-1]
        texto = (PREFIJO_ID.sub("", nombre) + " "
                 + (rec.get("description") or "")) # el slug empieza por el ID del recurso que contiene falsos anios # TODO revisar todos los datos
        anios = re.findall(r"(20\d{2})", texto)
        recursos.append({
            "url": url,
            "nombre": nombre,
            "descripcion": rec.get("description") or "",
            "formato": formato,
            "anios": anios,
        })
    return recursos, licencia

def filtrar_recursos(recursos: list[dict], clave: str) -> list[dict]:
    """Aplica tres filtros: anio en rango (o sin anio), formato permitido
    para el conjunto y, si existe, el regex de subserie del conjunto"""
    formatos = getattr(config, "FORMATOS_POR_CONJUNTO", {}).get(clave)
    patron = getattr(config, "FILTROS_RECURSO", {}).get(clave)
    elegidos = []
    for r in recursos:
        validos = [a for a in r["anios"] if int(a) in config.ANIOS]
        if r["anios"] and not validos:
            continue
        if formatos and r["formato"] not in formatos:
            continue
        if patron: # se filtra por descripcion, no por nombre: el slug repite las palabras del paquete y da falsos positivos con peatones/bicicletas
            if not re.search(patron, _normalizar(r["descripcion"] or r["nombre"])):
                continue
        r["anio"] = validos[0] if validos else ""
        elegidos.append(r)
    return elegidos


# --- funciones para guardar en destino --

def escribir(fs, base: str, relativo: str, contenido: bytes) -> str:
    ruta = f"{base.rstrip('/')}/{relativo}"
    try:  # para crear carpetas en local
        fs.makedirs(ruta.rsplit("/", 1)[0], exist_ok=True)
    except (NotImplementedError, PermissionError):
        pass
    with fs.open(ruta, "wb") as f:
        f.write(contenido)
    return ruta

def ya_existe(fs, base: str, relativo: str) -> bool:
    return fs.exists(f"{base.rstrip('/')}/{relativo}")

def registrar_metadato(fs, base: str, fila: dict) -> None:
    ruta = f"{base.rstrip('/')}/_metadatos.csv"
    existentes = ""
    if fs.exists(ruta):
        with fs.open(ruta, "r") as f:
            existentes = f.read()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(fila))
    if not existentes:
        w.writeheader()
    w.writerow(fila)
    with fs.open(ruta, "w") as f:
        f.write(existentes + buf.getvalue())

def descargar_con_reintentos(url: str, pkg: str) -> "requests.Response":
    """GET con Referer a la pagina del dataset y reintentos con backoff para  403/429/503 (proteccion anti-bot) 
    espera y recalienta la sesion para renovar cookies"""
    referer = f"https://datos.madrid.es/dataset/{pkg}"
    ultimo = None
    for intento in range(1, REINTENTOS + 1):
        ultimo = SESION.get(url, timeout=300, headers={"Referer": referer})
        if ultimo.status_code == 200:
            return ultimo
        if ultimo.status_code in (403, 429, 503) and intento < REINTENTOS:
            espera = 10 * intento
            print(f"         [{ultimo.status_code}] anti-bot; "
                  f"reintento {intento}/{REINTENTOS - 1} en {espera}s")
            time.sleep(espera)
            SESION.get(referer, timeout=60)  # renovar cookies
            continue
        break
    ultimo.raise_for_status()
    return ultimo


# --- funciones para descarga --

def nombre_seguro(texto: str) -> str:
    """Nombre de fichero legible a partir del nombre del recurso CKAN"""
    limpio = re.sub(r"[^\w.\-]+", "_", texto, flags=re.UNICODE).strip("_")
    return limpio[:120]

def procesar_conjunto(clave: str, fs, base: str, dry_run: bool) -> None:
    """
    procesa el flujo de descarga para un conjunto de datos específico:
      1. Resuelve el package_id consultando el catálogo configurado
      2. Obtiene los metadatos del paquete desde la API de CKAN
      3. Filtra los recursos válidos (por año y formato) y si el archivo ya existe en destino, lo omite
      4. Descarga y extrae el contenido aplicando protección anti-bot y reintentos
      5. Guarda metadatos

    Args:
        clave (str):    Identificador interno del conjunto de datos (ej. 'peatones').
        fs (str):       Sistema de archivos de destino (local, s3, gcs).
        base (str):     Ruta base o bucket de destino (ej. 'data/bronze').
        dry_run (bool): Si es True, solo imprime los recursos, no descarga
    """
    print(f"== Conjunto: {clave} ==")
    pkg = resolver_package_id(config.CATALOGOS[clave])
    if not pkg:
        print("  [AVISO] no se pudo resolver el package_id (¿URL correcta?)")
        return
    print(f"  [pkg ] {pkg}")
    try:
        recursos, licencia = recursos_del_paquete(pkg)
    except Exception as e:  # noqa: BLE001
        print(f"  [AVISO] API CKAN fallo: {e}")
        return
    recursos = filtrar_recursos(recursos, clave)
    if not recursos:
        print("  [AVISO] sin recursos de datos tras filtrar por anio")
        return

    fallos: list[str] = []
    for rec in recursos:
        ext = rec["url"].rsplit(".", 1)[-1].lower()
        ext = ext if ext in FORMATOS_DATOS else rec["formato"]
        prefijo = f"{rec['anio']}_" if rec["anio"] else ""
        nombre = f"{prefijo}{nombre_seguro(rec['nombre'])}.{ext}"
        relativo = f"{clave}/{nombre}"
        if dry_run:
            desc = rec["descripcion"][:60]
            print(f"  [list] ({rec['anio'] or 'unico'}, {rec['formato']}) "
                  f"{rec['nombre']}  |  {desc}")
            continue
        if ya_existe(fs, base, relativo):
            print(f"  [skip] {nombre}")
            continue
        print(f"  [get ] {nombre}")
        try:
            r = descargar_con_reintentos(rec["url"], pkg)
        except Exception as e:  # noqa: BLE001 - registrar y continuar
            print(f"  [fail] {nombre}: {e}")
            fallos.append(nombre)
            continue
        escribir(fs, base, relativo, r.content)
        time.sleep(PAUSA_ENTRE_DESCARGAS)

        if ext == "zip":
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for miembro in z.namelist():
                    if miembro.endswith("/"):
                        continue
                    nombre_m = f"{prefijo}{miembro.rsplit('/', 1)[-1]}"
                    escribir(fs, base, f"{clave}/{nombre_m}", z.read(miembro))
                    print(f"         + extraido {nombre_m}")

        registrar_metadato(fs, base, {
            "conjunto": clave,
            "package_id": pkg,
            "fichero": nombre,
            "url_origen": rec["url"],
            "fecha_descarga": datetime.now(timezone.utc).isoformat(),
            "bytes": len(r.content),
            "licencia": licencia,
        })
    if fallos:
        print(f"  [!!  ] {len(fallos)} fichero(s) fallidos en '{clave}': "
              f"re-ejecutar mas tarde (idempotente)")

# --- funciones principales --

def main() -> None:
    """Manejar los argunmentos de entrada y llamar a la funcion que procesa el conjunto del archivo config"""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("conjuntos", nargs="*", default=[],
                    help="claves de config.CATALOGOS (vacio = todos)")
    ap.add_argument("--destino", default=str(config.BRONZE),
                    help="ruta local o URL s3:// gs:// az://")
    ap.add_argument("--dry-run", action="store_true",
                    help="listar recursos sin descargar nada")
    args = ap.parse_args()

    claves = args.conjuntos or list(config.CATALOGOS)
    desconocidas = [c for c in claves if c not in config.CATALOGOS]
    if desconocidas:
        sys.exit(f"Conjuntos desconocidos: {desconocidas}. "
                 f"Validos: {list(config.CATALOGOS)}")

    fs, base = None, args.destino
    if not args.dry_run:
        fs, _ = fsspec.core.url_to_fs(args.destino)
        if not base.startswith(("s3://", "gs://", "az://", "abfs://")):
            fs.makedirs(base, exist_ok=True)

    for clave in claves:
        procesar_conjunto(clave, fs, base, args.dry_run)


if __name__ == "__main__":
    main()