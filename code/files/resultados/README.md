# Resultados

Salidas generadas por el pipeline. Se versionan para permitir contrastar las tablas y figuras de la memoria con los ficheros que las produjeron.

## isla_calor/

Dos ejecuciones completas del mismo análisis (`config.MODO_REPLICA`):

- `replica/`: reproduce las condiciones del TFG de referencia (sin criterio de cobertura mínima).
- `propio/`: aplica los criterios metodológicos de este trabajo (`MIN_DIAS_ANIO` días válidos mínimos por estación y año).


Cada carpeta contiene un subdirectorio por año con los diagramas del codo, dendrogramas, gráficos de correlación y las tablas de grupos por estació.
Tambien los resúmenes entre años (`resumen_silhouette.csv`, `resumen_arbolado.csv`), el gráfico de evolución y el log de la ejecución con su configuración.

`cobertura_temperatura.csv` (días válidos por estación y año) es común a ambos modos.