# Reto 1 · Perfiles ciudadanos de participación (Hackea la Participación, INE)

Pipeline reproducible de segmentación (clustering) sobre datos **agregados** de la Plataforma CCPC 2009-2024.

## Estructura
```
utils.py                         funciones y parámetros compartidos (lee su docstring)
01_carga_y_exploracion.ipynb     carga, limpieza, validación, EDA
02_ingenieria_de_variables.ipynb matriz de segmentos x elecciones + variables derivadas
03_clustering_y_seleccion_k.ipynb escalado, K-means ponderado, selección de k (4-6), estabilidad, comparación de algoritmos
04_perfiles_e_interpretacion.ipynb caracterización, nombres, fichas, exportación de tablas/figuras
data/raw/        <- coloca aquí el archivo descargado de la plataforma
data/processed/  <- se llena solo
outputs/         <- figuras (PNG 200 dpi) y tablas (CSV) listas para el documento
```

## Cómo correrlo
```bash
python -m venv .venv; .\.venv\Scripts\Activate.ps1      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab
```
Ejecuta los notebooks **en orden (01 → 04)**. Con ~25 mil segmentos todo tarda pocos minutos en una laptop.

## Datos
1. Descarga los datos agregados de la plataforma CCPC y guárdalos en `data/raw/ccpc_agregado.csv` (o .xlsx; ajusta `RUTA_DATOS`).
2. En `01_...ipynb` llena `COLUMN_MAP` para mapear tus columnas al esquema estándar:
   `anio, entidad, distrito, tipo_seccion, sexo, grupo_edad, lista_nominal, participantes`.
3. Si la base viene a nivel sección, el código la agrega a distrito automáticamente. Si viene en formato ancho, conviértela antes con `pd.melt`.
4. Sin archivo real, el proyecto usa **datos sintéticos** (aviso visible en cada notebook) solo para probar el código.

## Decisiones que debes documentar en el informe
Unidad de análisis, filtro de tamaño mínimo, imputación, escalado, ponderación, criterio de elección de k, estabilidad bootstrap y la **falacia ecológica** (datos agregados ⇒ perfiles de segmentos, no de individuos).

## Documento técnico (LaTeX) — carpeta `documento/`
```bash
cd documento
python generar_tablas_latex.py     # convierte outputs/tablas/*.csv en tablas y valores para el .tex
xelatex main.tex && xelatex main.tex
```
- Compilar con **XeLaTeX** (en Overleaf: Menú > Compiler > XeLaTeX). Sube también `outputs/figuras/` conservando la ruta relativa `../outputs/figuras/`.
- Arial 11, interlineado 1.5 (`\setstretch{1.5}`). Si Arial no está instalada usa Liberation Sans (misma métrica).
- `\guiatrue` muestra las cajas de guía; cambia a `\guiafalse` para la versión final y verifica 8-12 páginas.
- Todo lo que sale en rojo `[PENDIENTE: ...]` debe redactarse o confirmarse antes de entregar.
