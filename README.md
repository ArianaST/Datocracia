# Datocracia · Perfiles de participación

Análisis de los Conteos Censales de Participación Ciudadana del INE, 2009–2024.
La unidad es entidad × distrito federal de referencia × sexo × grupo de edad.

## Instalación y ejecución

El entorno local revisado utiliza Python 3.11. Desde la carpeta raíz de `Datocracia`, crear un entorno e instalar las dependencias:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --user --name datocracia --display-name "Python (Datocracia)"
.\.venv\Scripts\python.exe -m jupyterlab
```

Abrir los notebooks con el kernel **Python (Datocracia)** y ejecutar todas sus celdas en orden. Los comandos anteriores son para Windows/PowerShell. En otros sistemas, usar el ejecutable de Python del entorno en `bin/python`.

`requirements.txt` incluye el análisis numérico, GeoPandas para cartografía, Requests para descargarla, `threadpoolctl` para controlar los hilos del ajuste y JupyterLab/IPython/ipykernel para los notebooks. Declara versiones mínimas; no es un archivo de bloqueo del entorno. Para reutilizar modelos `.joblib`, conservar las versiones del entorno con el que se generaron o volver a ajustar el modelo.

## Datos e insumos requeridos

- **Conteos del INE:** colocar en `data/raw/` los CSV originales de 2009, 2012, 2015, 2018, 2021 y 2024. El notebook 01 busca `datosabiertos_deceyec_conteoscensal*.csv`; los diccionarios `01_descripcioncampos_conteoscensales*.txt` documentan los campos originales.
- **Correspondencias territoriales:** el notebook 02 requiere `data/raw/equivalencias_territoriales.csv`. Debe contener `anio`, `clave_entidad`, `clave_municipio`, `seccion`, `distrito_ref`, `marco_referencia` y `tipo_enlace`. La clave de origen debe ser única y completa. Se admiten enlaces `exacto` y `aproximado` hacia un único marco de referencia; los registros sin destino elegible se excluyen y se reportan. Los archivos ZIP en `data/raw/cartografia_oficial/` no sustituyen esta tabla ni se convierten automáticamente en equivalencias.
- **Base preparada:** el notebook 01 genera `data/processed/ccpc_limpio.csv.gz` y `FUENTE.txt` con el valor `REAL`. Los notebooks 02 y 03 comprueban esa procedencia y el esquema de las variables.
- **Mapa estatal:** el notebook 04 utiliza `data/processed/mexico_entidades.geojson`. Si no hay una copia legible, intenta descargarla del servicio de INEGI configurado en el código y guardarla en esa ruta. Para ejecutar sin conexión, proporcionar previamente el GeoJSON válido.

La versión preparada para GitHub conserva `equivalencias_territoriales.csv`: es un insumo necesario del notebook 02 y no se obtiene automáticamente de los ZIP cartográficos. También incluye las unidades, asignaciones, diagnósticos y el mapa estatal para trabajar con los resultados existentes.

Se omiten por tamaño los CSV originales de CCPC, `ccpc_limpio.csv.gz` y los ZIP de `data/raw/cartografia_oficial/`. La base limpia es una salida regenerable del notebook 01; los ZIP cartográficos no se leen en el flujo actual. Esta exclusión no modifica las variables ni el modelo.

Para ejecutar la versión publicada:

- **Volver a ajustar el clustering:** ejecutar 03 → 04 usando `data/processed/unidades.csv` y `FUENTE.txt`, incluidos en el repositorio.
- **Regenerar tablas y figuras:** ejecutar solo 04 usando `unidades_con_cluster.csv` y los diagnósticos del 03, también incluidos.
- **Reconstruir desde los conteos originales:** descargar los CSV de las 6 elecciones desde la [plataforma CCPC del INE](https://ine.mx/transparencia/datos-abiertos/visualizacion-datos/conteos-censales-participacion/), extraerlos directamente en `data/raw/` y ejecutar 01 → 02 → 03 → 04. El 01 genera `ccpc_limpio.csv.gz`; no se puede empezar en 02 si esa base todavía no existe.

## Estructura del proyecto

```text
Datocracia/
├── 01_carga_y_exploracion.ipynb
├── 02_ingenieria_de_variables.ipynb
├── 03_clustering_y_seleccion_k.ipynb
├── 04_perfiles_e_interpretacion.ipynb
├── utils.py
├── requirements.txt
├── data/
│   ├── raw/                  # Conteos y correspondencias territoriales
│   └── processed/            # Bases, asignaciones, modelo y mapa en caché
└── outputs/
    ├── tablas/               # Indicadores, composiciones y diagnósticos
    └── figuras/              # Gráficas, mapas y fichas por perfil
```

`utils.py` concentra las rutas, normalizaciones, indicadores, versiones del esquema y funciones compartidas.

## Flujo de los notebooks

1. **01 · Carga y exploración:** lee los archivos fuente, limpia conteos, conserva municipio y sección y guarda `data/processed/ccpc_limpio.csv.gz`.
2. **02 · Ingeniería de variables:** aplica las correspondencias distritales aproximadas, agrega conteos, evalúa cobertura y calcula los indicadores. Exporta `unidades.csv` y `unidades_diagnostico.csv`.
3. **03 · Clustering:** ajusta un único K-Means con seis perfiles y evalúa separación y estabilidad. Edad, sexo y territorio quedan fuera de la distancia.
4. **04 · Resultados:** presenta resultados generales y desgloses de territorio, edad, sexo y participación; termina con fichas cuantitativas con mapas. Los títulos son Perfil 0–5. La interpretación narrativa se redacta por el equipo fuera del código.

Ejecutar 01 → 02 → 03 → 04 para reconstruir el análisis. Si ya se dispone de las asignaciones vigentes y de las tablas `diagnostico_perfiles_participacion.csv` y `asociaciones_factores_participacion.csv` del 03, ejecutar solo 04 para regenerar tablas y fichas. Reiniciar el kernel antes de ejecutar un notebook tras cambios en `utils.py`.

## Variables de clustering

| Indicador | Definición | Unidad |
|---|---|---|
| Participación media | Promedio de las seis tasas | % |
| Brecha presidencial–intermedia | Diferencia entre promedios por tipo electoral | pp |
| Cambio reciente | [(p2021 − p2015) + (p2024 − p2018)] / 12 | pp/año |
| Irregularidad de trayectoria | Raíz del promedio de residuos cuadrados frente a nivel, efecto de tipo electoral y tendencia lineal común | pp |

Las tasas son SV/(LN−NS); p se expresa en porcentaje. Se exigen seis elecciones observadas, sin imputación, y un denominador mínimo de 30 por elección. Las variables relativas a edad y sexo, la tendencia histórica y las curvaturas son diagnósticos.

K-Means utiliza StandardScaler, pesos proporcionales a raíz del denominador medio, 50 inicializaciones y semilla 42. El número de perfiles se fija en seis. La estabilidad usa 20 submuestras de 25 de las 32 entidades, reajustando escalador y modelo. El ARI compara las particiones predichas del universo completo; Jaccard compara integrantes por perfil. La silueta preliminar usa hasta 2,000 filas; la exportada al final es exacta sobre todas las filas elegibles.

## Lectura de los resultados

Los indicadores por perfil usan los pesos del ajuste. Las curvas suman participantes y denominadores de cada elección. La composición por edad, sexo y región utiliza LN media; se acompaña de proporciones por número de segmentos.

Los mapas muestran el porcentaje de LN media estatal incluida que corresponde a cada perfil. No representan distritos individuales ni personas únicas. Las tablas distritales conservan el detalle territorial. Los colores usan una escala común entre fichas.

Las etiquetas numéricas se ordenan por participación media. El notebook 04 no genera nombres interpretativos ni descripciones automáticas. Sus tablas y fichas aportan evidencia para que el equipo redacte el análisis humano.

## Salidas vigentes

- `data/processed/unidades_con_cluster.csv`: segmentos y asignaciones.
- `data/processed/modelo_clustering_participacion.joblib`: modelo, escalador y metadatos.
- `outputs/tablas/metricas_seleccion_k_participacion.csv`: métricas del único modelo de seis perfiles; el nombre se conserva por compatibilidad.
- `outputs/tablas/perfil_resumen_participacion.csv`: identificadores numéricos e indicadores, sin narrativa generada.
- `data/processed/segmentos_con_perfil_participacion.csv`: asignaciones con la etiqueta numérica de cada perfil.
- `outputs/tablas/diagnostico_perfiles_participacion.csv` y `asociaciones_factores_participacion.csv`: diagnósticos usados por el notebook 04.
- `outputs/tablas/presencia_perfil_distrito_participacion.csv` y `presencia_perfil_entidad_participacion.csv`: distribución territorial dentro de cada distrito y estado.
- `outputs/tablas/trayectorias_estandarizadas_participacion.csv` y `brechas_crudas_estandarizadas_participacion.csv`: comparación de trayectorias y brechas tras estandarizar por edad.
- `outputs/figuras/resultados_generales_participacion.png` y `mapas_presencia_estatal_perfiles_participacion.png`: panorama general y mapas comparables.
- `outputs/tablas/contraste_perfiles_participacion.csv`: diferencias numéricas entre centros vecinos.
- `outputs/figuras/ficha_perfil_0_participacion.png` a `ficha_perfil_5_participacion.png`: seis fichas con mapa, trayectoria y composición.

Las salidas del modelo vigente usan el sufijo `_participacion`. `benchmark_nacional_edad.csv` corresponde al preprocesamiento. Los entregables disponibles en la raíz son:

- `Reporte_final_Datocracia_documento_tecnico.pdf`.
- `Fichas_de_perfiles_Datocracia.pdf`.
- `Presentacion_ejecutiva_Datocracia.pptx`.

Estos documentos se preparan por separado: ejecutar los notebooks no regenera los PDF ni la presentación.

Los resultados son descriptivos. Las correspondencias territoriales son aproximadas, no se sigue a las mismas personas y seis grupos no implica seis tipos naturales de ciudadanía. La irregularidad puede recoger cambios reales o problemas de comparabilidad. Las métricas y distribuciones internas permiten evaluar el solapamiento.
