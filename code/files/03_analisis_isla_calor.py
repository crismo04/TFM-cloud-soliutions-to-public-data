"""
Replica y extension del TFG "Madrid, isla de calor" (clustering + correlaciones) para el año original (2021) y para el resto de años disponibles (extension)

Equivalencias R -> Python usadas como linea base de validacion:
  factoextra::fviz_nbclust (codo)   -> inercia de KMeans para k=1..10
  stats::kmeans                     -> sklearn.cluster.KMeans
  stats::hclust + dendrograma       -> scipy.cluster.hierarchy (ward)
  correlaciones                     -> pandas .corr() + scatter

El analisis guarda cada año en una subcarpeta de resultados. Ademas del clustering, se cruza el arbolado con el clima por distrito

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
import config

ANIO_REPLICA = 2021  # año del TFG original
MIN_DIAS_ANIO = 300  # TODO comentar en memoria, para que no descuadre si hay algun año que faltan datos

# TODO esto no lo tiene el TFG original, revisar y comentar para las diferencias como una mejora metodologica

# Aproximaciones originales (cap. 6):
#   nombre, conjunto de datos, magnitudes empleadas y k elegido
APROXIMACIONES = [
    ("meteo_todas_magnitudes", "meteo_diario", ["vel_viento", "dir_viento", "temperatura", "humedad_rel", "presion", "rad_solar", "precipitacion"], 4),
    ("meteo_temp_humedad", "meteo_diario", ["temperatura", "humedad_rel"], 5),
    ("meteo_temperatura", "meteo_diario", ["temperatura"], 4),
    ("contaminacion_no2", "calidad_aire_diario", ["no2"], 5),
    ("contaminacion_no2_pm", "calidad_aire_diario", ["no2", "pm25", "pm10"], 4),
]


# --- utilidades --

def _sin_tildes(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode() # pasar a formato asci

def _leer_silver(nombre: str) -> pd.DataFrame:
    """Lee parquet si puede y si no csv (transformando las fechas)"""
    try:
        return pd.read_parquet(config.SILVER / f"{nombre}.parquet")
    except (ImportError, FileNotFoundError):
        df = pd.read_csv(config.SILVER / f"{nombre}.csv")
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
    parciales = cobertura < MIN_DIAS_ANIO
    if parciales.any():
        print(f"    [info] {parciales.sum()} estaciones con <{MIN_DIAS_ANIO} dias de datos, se excluyen")
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
    plt.savefig(carpeta / f"codo_{nombre}.png", dpi=150)
    plt.close()

def ejecutar_aproximacion(nombre, clave, columnas, k, anio, carpeta):
    """principal para el analisis. Estandariza los valores, Agrupa por K-means y por dendogramas"""
    df = cargar(clave, anio)
    m = matriz_estaciones(df, columnas)
    if len(m) <= k:
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
    plt.savefig(carpeta / f"dendrograma_{nombre}.png", dpi=150)
    plt.close()
    m.to_csv(carpeta / f"clusters_{nombre}.csv")
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
            plt.savefig(carpeta / f"corr_{a}_{b}.png", dpi=150)
            plt.close()
    pd.DataFrame(filas).to_csv(carpeta / "correlaciones.csv", index=False)
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

def _estaciones_con_distrito():
    """Asigna cada estacion meteo a su distrito con el shapefile municipal de geopandas"""
    import geopandas as gpd
    shp = next((config.BRONZE / "distritos").glob("*.shp"))
    distritos = gpd.read_file(shp).to_crs(4326)
    col_nombre = next(c for c in distritos.columns if "NOMBRE" in c.upper() or "DISTRI" in c.upper())
    est = _leer_silver("estaciones_meteo")

    puntos = gpd.GeoDataFrame( est, geometry=gpd.points_from_xy(est["LONGITUD"], est["LATITUD"]), crs=4326)
    cruce = gpd.sjoin(puntos, distritos[[col_nombre, "geometry"]], predicate="within")
    cruce["distrito"] = cruce[col_nombre].map(_sin_tildes).str.upper().str.strip()
    return cruce[["CODIGO_CORTO", "distrito"]] if "CODIGO_CORTO" in cruce else cruce[[est.columns[0], "distrito"]] \
            .rename(columns={est.columns[0]: "CODIGO_CORTO"})

def analisis_arbolado(anio: int, carpeta) -> None:
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
    arbolado = _leer_silver("arbolado_masas_anual")
    arbolado = arbolado[arbolado["ANIO"] == anio].copy()
    if arbolado.empty:
        print(f"  [AVISO] sin arbolado de {anio}; se omite")
        return
    arbolado["distrito"] = (arbolado["DISTRITO"].map(_sin_tildes).str.upper().str.strip())

    # la superficie en hectareas no siempre se publica. 2019 solo traen m2. Se toma la columna en ha si existe y, si no, se calcula de los m2 (1 ha = 10.000 m2).
    #  Otra variante del schema drift del portal # TODO comentar memoria
    ha = _coalesce(arbolado, ["SUPERFICIE_MASA_FORESTAL_HA", "SUPERFICIE_MASA_ARBOREA_HA", "SUPERFICIE_(HA)_MASA_ARBOREA"])
    m2 = _coalesce(arbolado, ["SUPERFICIE_MASA_FORESTAL_M2", "SUPERFICIE_MASA_ARBOREA_M2", "SUPERFICIE_(M2)_MASA_ARBOREA"])
    ha = pd.to_numeric(ha, errors="coerce")
    m2 = pd.to_numeric(m2, errors="coerce")
    arbolado["superficie_ha"] = ha.fillna(m2 / 10_000)

    # temperatura media anual por estacion -> media por distrito
    meteo = cargar("meteo_diario", anio)
    g = meteo.groupby("estacion")["temperatura"]
    validas = g.count() >= MIN_DIAS_ANIO  # misma regla de cobertura que el clustering, evitar años con pocos datos
    temp = g.mean()[validas].rename("temperatura").reset_index()
    temp = temp.merge(estaciones, left_on="estacion", right_on="CODIGO_CORTO")
    por_distrito = temp.groupby("distrito")["temperatura"].mean().reset_index()
    cruce = por_distrito.merge( arbolado[["distrito", "superficie_ha"]], on="distrito")
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
    plt.savefig(carpeta / "arbolado_vs_temperatura.png", dpi=150)
    plt.close()
    cruce.to_csv(carpeta / "arbolado_temperatura_distrito.csv", index=False)
    print(f"  [OK] arbolado vs temperatura: {n_distritos} distritos, r={r:.3f}")

    # TODO comentar despues que esto es solo para ver por pantalla ahora
    return {"anio": anio, "r_arbolado": round(r, 3), "n_distritos": n_distritos}


# --- principal --

def resumen(filas_clusters: list[dict], filas_arbolado: list[dict]) -> None:
    """Tabla comparativa entre años + deteccion simple de anomalias, para no tener que abrir los CSV de cada año uno por uno"""
    if filas_clusters:
        piv = (pd.DataFrame(filas_clusters).pivot(index="anio", columns="aproximacion", values="silhouette"))
        print("\n== Resumen: silhouette por año y aproximacion ==")
        print(piv.round(3).to_string())
        config.RESULTADOS.mkdir(parents=True, exist_ok=True)
        piv.to_csv(config.RESULTADOS / "isla_calor" / "resumen_silhouette.csv")
    if filas_arbolado:
        arb = pd.DataFrame(filas_arbolado).set_index("anio")
        print("\n== Resumen: correlacion arbolado vs temperatura por año ==")
        print(arb.to_string())
        arb.to_csv(config.RESULTADOS / "isla_calor" / "resumen_arbolado.csv")
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
    tabla.to_csv(config.RESULTADOS / "isla_calor" / "cobertura_temperatura.csv")
    print("\n== Cobertura: dias validos de temperatura por estacion y año ==")
    print(tabla.to_string())

def main() -> None:
    anios = [int(a) for a in sys.argv[1:]] or config.ANIOS
    todos_clusters, todos_arbolado = [], []
    for anio in anios:
        etiqueta = "replica del TFG" if anio == ANIO_REPLICA else "extension"
        print(f"== Isla de calor {anio} ({etiqueta}) ==")
        carpeta = config.RESULTADOS / "isla_calor" / str(anio)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, clave, columnas, k in APROXIMACIONES:
            try:
                fila = ejecutar_aproximacion(nombre, clave, columnas, k, anio, carpeta)
                if fila:
                    todos_clusters.append(fila)
            except FileNotFoundError:
                print(f"  [AVISO] falta silver de '{clave}'; ejecutar 01 y 02")
                return
        correlaciones(anio, carpeta)
        fila_arb = analisis_arbolado(anio, carpeta)
        if fila_arb:
            todos_arbolado.append(fila_arb)
    resumen(todos_clusters, todos_arbolado)
    cobertura_temperatura()

if __name__ == "__main__":
    main()