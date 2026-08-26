"""
Replica y extension del TFG "Madrid, isla de calor" (clustering + correlaciones) para el año original (2021) y para el resto de años disponibles (extension)

Equivalencias R -> Python usadas como linea base de validacion:
  factoextra::fviz_nbclust (codo)   -> inercia de KMeans para k=1..10
  stats::kmeans                     -> sklearn.cluster.KMeans
  stats::hclust + dendrograma       -> scipy.cluster.hierarchy (ward)
  correlaciones                     -> pandas .corr() + scatter

El analisis guarda cada año en una subcarpeta de resultados. Ademas del clustering, se cruza el arbolado con el clima por distrito

# TODO hay cosas que quizas habria que mover al proceso de silver, ya que he tenido que limpiar muchos datos

Uso:
  python 03_analisis_isla_calor.py         # replica 2021 + extension
  python 03_analisis_isla_calor.py 2021    # solo un año
"""
import sys
import unicodedata
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from pathlib import Path


import config

class _Tee:
    """Duplica la salida por pantalla y en un fichero de log, para dejar constancia de cada ejecucion sin perder el seguimiento en vivo"""
    def __init__(self, ruta):
        self.fichero = open(ruta, "w", encoding="utf-8")
    def write(self, texto):
        sys.__stdout__.write(texto)
        self.fichero.write(texto)
    def flush(self):
        sys.__stdout__.flush()
        self.fichero.flush()

ANIO_REPLICA = 2021  # año del TFG original
# MIN_DIAS_ANIO = 300  # TODO comentar en memoria, para que no descuadre si hay algun año que faltan datos
# TODO esto no lo tiene el TFG original, comentar para las diferencias como una mejora metodologica   -- movido a config

# Aproximaciones originales (cap. 6):
#   nombre, conjunto de datos, magnitudes empleadas, variables externas y k elegido
APROXIMACIONES = [
    ("meteo_todas_magnitudes", "meteo_diario", ["vel_viento", "dir_viento", "temperatura", "humedad_rel", "presion", "rad_solar", "precipitacion"], [], 4),
    ("meteo_temp_humedad", "meteo_diario", ["temperatura", "humedad_rel"], [], 5),
    ("meteo_temp_arbolado", "meteo_diario", ["temperatura"], ["superficie_ha"], 4), #TODO añadir a la memoria que su temperatura tiene temp y arbolado (ponia solo temperatura)
    ("contaminacion_no2", "calidad_aire_diario", ["no2"], [], 5),
    ("contaminacion_no2_pm", "calidad_aire_diario", ["no2", "pm25", "pm10"], [], 4),
]

# --- utilidades --

def _sin_tildes(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode() # pasar a formato asci

def _leer_silver(nombre: str) -> pd.DataFrame:
    """Lee parquet si puede y si no csv (transformando las fechas)"""
    try:
        return pd.read_parquet(f"{config.SILVER}/{nombre}.parquet")
    except (ImportError, FileNotFoundError):
        df = pd.read_csv(f"{config.SILVER}/{nombre}.csv")
        for col in ("fecha", "FECHA"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        return df

def cargar(clave: str, anio: int) -> pd.DataFrame:
    df = _leer_silver(f"{clave}_diario")
    return df[df["fecha"].dt.year == anio] # Nos quedamos solo con el año que nos interesa


# --- clustering por estacion (aproximaciones originales) --

def matriz_estaciones(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Media anual por estacion de las magnitudes pedidas. Se descartan las estaciones sin datos en alguna magnitud"""
    cols = [c for c in columnas if c in df.columns]
    g = df.groupby("estacion")[cols]
    m = g.mean()
     # dias de la magnitud peor cubierta, para no tener en cuenta datos sesgados
    cobertura = g.count().min(axis=1)
    parciales = cobertura < config.MIN_DIAS_ANIO
    if parciales.any():
        print(f"    [info] {parciales.sum()} estaciones con <{config.MIN_DIAS_ANIO} dias de datos, se excluyen")
    m = m[~parciales]
    completas = m.dropna(how="any") # KMeans no soporta bien nulos # TODO revisar si cambair por media o algo
    if len(completas) < len(m):
        print(f"    [info] {len(m) - len(completas)} estaciones sin cobertura " f"completa de magnitudes, quedan {len(completas)}")
    return completas

def codo(X: np.ndarray, nombre: str, carpeta) -> None:
    """Metodo de codo para visualizar la inercia"""
    ks = range(1, min(10, len(X)) + 1)
    inercias = [KMeans(n_clusters=k, n_init=10, random_state=100).fit(X).inertia_ for k in ks] # TODO revisar si 4 o 5 es la mejor
    plt.figure(figsize=(6, 4))
    plt.plot(list(ks), inercias, "o-")
    plt.xlabel("k"); plt.ylabel("Inercia"); plt.title(f"Diagrama del codo: {nombre}")
    plt.tight_layout()
    plt.savefig(f"{carpeta}/codo_{nombre}.png", dpi=150)
    plt.close()

def ejecutar_aproximacion(nombre, clave, columnas, externas, k, anio, carpeta) -> dict | None:
    """principal para el analisis. Estandariza los valores, Agrupa por K-means y por dendogramas"""
    df = cargar(clave, anio)
    m = matriz_estaciones(df, columnas)
    if externas:
        m.index = m.index.astype(int)
    for var in externas:
        try:
            m = m.join(EXTERNAS[var](anio), how="inner").dropna()
        except (ImportError, FileNotFoundError, StopIteration) as e:
            print(f"    [AVISO] {nombre}: sin '{var}' ({e}); se sigue sin esa variable")
    if len(m) < k + 1:  # sin holgura el clustering degenera, omito grupos pequeños
        print(f"  [AVISO] {nombre}: solo {len(m)} estaciones con datos, se omite")
        return
    X = StandardScaler().fit_transform(m.values)
    codo(X, nombre, carpeta) # Dibujamos el codo

    # kmeans con la misma semilla que la referencia
    km = KMeans(n_clusters=k, n_init=25, random_state=100).fit(X)
    m[f"kmeans_k{k}"] = km.labels_

    sil = silhouette_score(X, km.labels_)  # metrica para comparar los grupos

    # jerarquico ward (Dendrograma)
    Z = linkage(X, method="ward")
    m[f"jerarquico_k{k}"] = fcluster(Z, t=k, criterion="maxclust")

    # pintamos todo
    plt.figure(figsize=(8, 4))
    dendrogram(Z, labels=[str(int(e)) for e in m.index])
    plt.title(f"Dendrograma (ward): {nombre} {anio}")
    plt.tight_layout()
    plt.savefig(f"{carpeta}/dendrograma_{nombre}.png", dpi=150)
    plt.close()
    m.to_csv(f"{carpeta}/clusters_{nombre}.csv")
    print(f"  [OK] {nombre}: {len(m)} estaciones, k={k}, " f"inercia={km.inertia_:.1f}, silhouette={sil:.3f}")

    # TODO comentar despues que esto es solo para ver por pantalla ahora
    return {"anio": anio, "aproximacion": nombre, "n_estaciones": len(m), "silhouette": round(sil, 3)}


# --- correlaciones meteorologicas (cap. 6.3 del TFG) --

def correlaciones(anio: int, carpeta) -> None:
    """Para buscar las relacciones entre variables (pares) por estacion, generando graficos de dispersion"""
    meteo = cargar("meteo_diario", anio)
    filas = []
    pares = [("temperatura", "humedad_rel"), ("precipitacion", "rad_solar")]
    for a, b in pares:
        if a in meteo.columns and b in meteo.columns:
            medias = meteo.groupby("estacion")[[a, b]].mean().dropna()
            r = medias[a].corr(medias[b])
            filas.append({"par": f"{a} vs {b}", "pearson_r": round(r, 3), "n_estaciones": len(medias)})
            ax = medias.plot.scatter(x=a, y=b, figsize=(5, 4))
            ax.set_title(f"{a} vs {b} (r={r:.2f})")
            plt.tight_layout()
            plt.savefig(f"{carpeta}/corr_{a}_{b}.png", dpi=150)
            plt.close()
    pd.DataFrame(filas).to_csv(f"{carpeta}/correlaciones.csv", index=False)
    print(f"  [OK] correlaciones: {len(filas)} pares")


# --- cruce arbolado x clima por distrito --

def _coalesce(df: pd.DataFrame, columnas: list[str]) -> pd.Series:
    """Primera columna no nula de la lista (el arbolado renombro la misma magnitud tres veces a lo largo de los años)""" # TODO añadir a MEMORIA Schema Drift?????
    presentes = [c for c in columnas if c in df.columns]
    if not presentes:                       # ese año no publica esta magnitud
        return pd.Series(np.nan, index=df.index)
    s = df[presentes[0]].copy()
    for c in presentes[1:]:
        s = s.fillna(df[c])
    return s

def _norm_distrito(s: pd.Series) -> pd.Series:
    """Normaliza nombres de distrito quitando espacios en los guiones""" # TODO añadir a memoria mas problemas
    return (s.map(_sin_tildes).str.upper().str.replace(r"\s*-\s*", "-", regex=True).str.replace(r"\s+", " ", regex=True).str.strip())

def _superficie_por_distrito(anio: int) -> pd.Series:
    """Superficie arborea (ha) por distrito para un año, con el coalesce de las tres denominaciones y la derivacion desde m2"""
    arb = _leer_silver("arbolado_masas_anual")
    arb = arb[arb["ANIO"] == anio].copy()
    arb["distrito"] = _norm_distrito(arb["DISTRITO"])
    ha = pd.to_numeric(_coalesce(arb, ["SUPERFICIE_MASA_FORESTAL_HA", "SUPERFICIE_MASA_ARBOREA_HA", "SUPERFICIE_(HA)_MASA_ARBOREA"]), errors="coerce")
    m2 = pd.to_numeric(_coalesce(arb, ["SUPERFICIE_MASA_FORESTAL_M2", "SUPERFICIE_MASA_ARBOREA_M2", "SUPERFICIE_(M2)_MASA_ARBOREA"]), errors="coerce")
    arb["superficie_ha"] = ha.fillna(m2 / 10_000)
    return arb.set_index("distrito")["superficie_ha"]

def _superficie_por_estacion(anio: int) -> pd.Series:
    """Superficie arborea del distrito de cada estacion (sjoin + tabla anual)"""
    est = _estaciones_con_distrito().copy()
    # el codigo de estacion puede venir como texto o float -> paso a int
    est["CODIGO_CORTO"] = pd.to_numeric(est["CODIGO_CORTO"], errors="coerce")
    est = est.dropna(subset=["CODIGO_CORTO"])
    est["CODIGO_CORTO"] = est["CODIGO_CORTO"].astype(int)
    s = est.set_index("CODIGO_CORTO")["distrito"].map(_superficie_por_distrito(anio)).rename("superficie_ha")
    # los distritos con 0 ha se descartan: el trabajo original exige "tener datos de masas arboreas" y parece interpretar el 0 como ausencia # TODO memoria
    return s[s > 0]

def _estaciones_con_distrito():
    """Asigna cada estacion meteo a su distrito con el shapefile municipal de geopandas"""
    import geopandas as gpd
    shp = next(Path(f"{config.BRONZE}/distritos").glob("*.shp"))
    distritos = gpd.read_file(shp).to_crs(4326)
    col_nombre = next(c for c in distritos.columns if "NOMBRE" in c.upper() or "DISTRI" in c.upper())
    est = _leer_silver("estaciones_meteo")

    puntos = gpd.GeoDataFrame( est, geometry=gpd.points_from_xy(est["LONGITUD"], est["LATITUD"]), crs=4326)
    cruce = gpd.sjoin(puntos, distritos[[col_nombre, "geometry"]], predicate="within")
    cruce["distrito"] = _norm_distrito(cruce[col_nombre])
    return cruce[["CODIGO_CORTO", "distrito"]] if "CODIGO_CORTO" in cruce else cruce[[est.columns[0], "distrito"]] \
            .rename(columns={est.columns[0]: "CODIGO_CORTO"})

def analisis_arbolado(anio: int, carpeta) ->  dict | None:
    """Correlacion entre superficie de masas arboreas y temperatura media del distrito (conclusion):
        - Calcula la temperatura media de cada estación y asigna esa temperatura a un distrito.
        - Cruza esos datos con las hectáreas de masa arbórea de ese distrito y calcula si a más árboles, menos temperatura.
    """
    try:
        estaciones = _estaciones_con_distrito()
    except ImportError:
        print("  [AVISO] sin geopandas; se omite el cruce con arbolado")
        return
    except (StopIteration, FileNotFoundError):
        print("  [AVISO] falta el shapefile de distritos en bronze; se omite")
        return

    # la superficie en hectareas no siempre se publica. 2019 solo traen m2. Se toma la columna en ha si existe y, si no, se calcula de los m2 (1 ha = 10.000 m2).
    #  Otra variante del schema drift del portal # TODO comentar memoria
    superficie = _superficie_por_distrito(anio)
    if superficie.empty:
        print(f"  [AVISO] sin arbolado de {anio}; se omite")
        return

    # temperatura media anual por estacion -> media por distrito
    meteo = cargar("meteo_diario", anio)
    g = meteo.groupby("estacion")["temperatura"]
    validas = g.count() >= config.MIN_DIAS_ANIO  # misma regla de cobertura que el clustering, evitar años con pocos datos
    temp = g.mean()[validas].rename("temperatura").reset_index()
    temp = temp.merge(estaciones, left_on="estacion", right_on="CODIGO_CORTO")
    por_distrito = temp.groupby("distrito")["temperatura"].mean().reset_index()
    cruce = por_distrito.merge(superficie.reset_index(), on="distrito")
    if len(cruce) < 3:      # Solo si hay mas de 3 puntos, si no  no tiene sentido
        print(f"  [AVISO] solo {len(cruce)} distritos con estacion y arbolado")
        return

    # corr por pares: algun año una estacion tiene temperatura pero nov arbolado (o al reves) y un solo NaN anularia toda la correlacion # TODO revisar este fix que me tengo que ir
    valido = cruce[["temperatura", "superficie_ha"]].dropna()
    r = valido["temperatura"].corr(valido["superficie_ha"])
    n_distritos = len(valido)

    ax = cruce.plot.scatter(x="superficie_ha", y="temperatura", figsize=(5, 4))
    for _, fila in cruce.iterrows():
        ax.annotate(fila["distrito"][:10], (fila["superficie_ha"], fila["temperatura"]), fontsize=6)
    ax.set_title(f"Arbolado vs temperatura por distrito {anio} (r={r:.2f})")
    plt.tight_layout()
    plt.savefig(f"{carpeta}/arbolado_vs_temperatura.png", dpi=150)
    plt.close()
    cruce.to_csv(f"{carpeta}/arbolado_temperatura_distrito.csv", index=False)
    print(f"  [OK] arbolado vs temperatura: {n_distritos} distritos, r={r:.3f}")

    # TODO comentar despues que esto es solo para ver por pantalla ahora
    return {"anio": anio, "r_arbolado": round(r, 3), "n_distritos": n_distritos}


# --- principal --

def grafico_evolucion(filas_arbolado: list[dict], base) -> None:
    """Grafico resumen: evolucion de la correlacion arbolado-temperatura.
    Si ya existe el resumen del otro modo, se superpone para ver el analisis de sensibilidad de un vistazo"""
    if not filas_arbolado:
        return
    arb = pd.DataFrame(filas_arbolado).set_index("anio").sort_index()
    plt.figure(figsize=(7, 4))
    plt.plot(arb.index, arb["r_arbolado"], "o-", label=f"modo {config.ETIQUETA_MODO}")
    otro = "replica" if config.ETIQUETA_MODO == "propio" else "propio"
    ruta_otro = f"{config.RESULTADOS}/isla_calor/{otro}/resumen_arbolado.csv"
    if Path(ruta_otro).exists():
        prev = pd.read_csv(ruta_otro).set_index("anio").sort_index()
        plt.plot(prev.index, prev["r_arbolado"], "s--", label=f"modo {otro}")
    plt.axhline(0, color="grey", linewidth=.8)
    plt.xlabel("Año"); plt.ylabel("r de Pearson")
    plt.title("Superficie arborea vs temperatura media por distrito")
    plt.legend(); plt.tight_layout()
    plt.savefig(f"{base}/evolucion_correlacion.png", dpi=150)
    plt.close()

def resumen(filas_clusters: list[dict], filas_arbolado: list[dict], base)-> None:
    """Tabla comparativa entre años + deteccion simple de anomalias, para no tener que abrir los CSV de cada año uno por uno"""
    if filas_clusters:
        piv = (pd.DataFrame(filas_clusters).pivot(index="anio", columns="aproximacion", values="silhouette"))
        print("\n== Resumen: silhouette por año y aproximacion ==")
        print(piv.round(3).to_string())
        piv.to_csv(f"{base}/resumen_silhouette.csv")
    if filas_arbolado:
        arb = pd.DataFrame(filas_arbolado).set_index("anio")
        print("\n== Resumen: correlacion arbolado vs temperatura por año ==")
        print(arb.to_string())
        arb.to_csv(f"{base}/resumen_arbolado.csv")
        r = arb["r_arbolado"].dropna() # marca outliers
        fuera = r[(r - r.mean()).abs() > 1.5 * r.std()]
        media = f"{r.mean():.3f}" if len(r) else "n/d"
        print(f"\n  media r = {media} (n={len(r)} años)")
        for anio, val in fuera.items():
            print(f"  [!] {anio}: r={val:.3f} se desvia del patron, revisar dato")

def cobertura_temperatura() -> None:
    """Diagnostico: dias validos de temperatura por estacion y año, para estudiar la caida de cobertura 2021-2022 (¿sincronizada con el hueco de aforos?)"""
    meteo = _leer_silver("meteo_diario_diario")
    meteo["anio"] = meteo["fecha"].dt.year
    tabla = (meteo.dropna(subset=["temperatura"]).groupby(["estacion", "anio"]).size().unstack(fill_value=0))
    tabla.to_csv(f"{config.RESULTADOS}/isla_calor/cobertura_temperatura.csv")
    print("\n== Cobertura: dias validos de temperatura por estacion y año ==")
    plt.figure(figsize=(7, 8))
    plt.imshow(tabla.values, aspect="auto", cmap="YlOrRd_r", vmin=0, vmax=366)
    plt.colorbar(label="dias validos")
    plt.xticks(range(len(tabla.columns)), tabla.columns, rotation=45)
    plt.yticks(range(len(tabla.index)), tabla.index, fontsize=7)
    plt.xlabel("Año"); plt.ylabel("Estacion")
    plt.title("Cobertura de temperatura por estacion y año")
    plt.tight_layout()
    plt.savefig(f"{config.RESULTADOS}/isla_calor/cobertura_temperatura.png", dpi=150)
    plt.close()
    print(tabla.to_string())


# --- principal --

EXTERNAS = {
    "superficie_ha": _superficie_por_estacion,
    # TODO mejoras: "altitud" (maestro de estaciones), "superficie_relativa"
}

def main() -> None:
    anios = [int(a) for a in sys.argv[1:]] or config.ANIOS
    todos_clusters, todos_arbolado = [], []
    base = f"{config.RESULTADOS}/isla_calor/{config.ETIQUETA_MODO}"
    Path(base).mkdir(parents=True, exist_ok=True)
    sys.stdout = _Tee(f"{base}/ejecucion.log")
    print(f"# ejecucion {pd.Timestamp.now():%Y-%m-%d %H:%M} | MODO_REPLICA={config.MODO_REPLICA} | MIN_DIAS_ANIO={config.MIN_DIAS_ANIO}")
    for anio in anios:
        etiqueta = "replica" if anio == ANIO_REPLICA else "extension"
        print(f"== Isla de calor {anio} ({etiqueta}) ==")
        carpeta = f"{base}/{anio}"
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        for nombre, clave, columnas, externas, k in APROXIMACIONES:
            try:
                fila = ejecutar_aproximacion(nombre, clave, columnas, externas, k, anio, carpeta)
                if fila:
                    todos_clusters.append(fila)
            except FileNotFoundError:
                print(f"  [AVISO] falta silver de '{clave}'; ejecutar 01 y 02")
                return
        correlaciones(anio, carpeta)
        fila_arb = analisis_arbolado(anio, carpeta)
        if fila_arb:
            todos_arbolado.append(fila_arb)

    resumen(todos_clusters, todos_arbolado, base)
    grafico_evolucion(todos_arbolado, base)
    cobertura_temperatura()

if __name__ == "__main__":
    main()