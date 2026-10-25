# -*- coding: utf-8 -*-
"""
utils.py — Configuración y funciones compartidas del proyecto
=============================================================
Reto 1 · Perfiles ciudadanos de participación (Hackea la Participación, INE)

Este módulo concentra TODO lo que se repite entre notebooks:
  * rutas del proyecto y parámetros globales (semilla, elecciones, regiones),
  * carga y limpieza de la base agregada de la Plataforma CCPC,
  * un generador de datos SINTÉTICOS para probar el pipeline sin los datos reales,
  * construcción de la "matriz de unidades" sobre la que se hace clustering,
  * pequeñas utilidades (media ponderada, orden de grupos de edad).

Idea clave del diseño
---------------------
La unidad de análisis es un SEGMENTO TERRITORIAL-DEMOGRÁFICO:

    (entidad, distrito, tipo_seccion, sexo, grupo_edad)

y cada segmento se describe por su HISTORIAL de participación (tasa en cada
elección federal 2009-2024). El clustering agrupa segmentos con historiales
parecidos; la edad, el sexo, la región, etc. se usan para CARACTERIZAR los
grupos (no para formarlos), de modo que los perfiles salgan del comportamiento.
"""
from __future__ import annotations

import re
import unicodedata
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# 1. Rutas y parámetros globales
# --------------------------------------------------------------------------- #
RAIZ = Path(__file__).resolve().parent
DIR_RAW = RAIZ / "data" / "raw"           # aquí pones el archivo descargado de la CCPC
DIR_PROC = RAIZ / "data" / "processed"    # datos intermedios generados por los notebooks
DIR_FIG = RAIZ / "outputs" / "figuras"
DIR_TAB = RAIZ / "outputs" / "tablas"
for _d in (DIR_RAW, DIR_PROC, DIR_FIG, DIR_TAB):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 42  # reproducibilidad: misma semilla => mismos resultados

# Elecciones federales cubiertas (diputaciones federales) y su tipo.
ELECCIONES = {
    2009: "intermedia", 2012: "presidencial", 2015: "intermedia",
    2018: "presidencial", 2021: "intermedia", 2024: "presidencial",
}
ANIOS = sorted(ELECCIONES)
ANIOS_PRES = [a for a in ANIOS if ELECCIONES[a] == "presidencial"]
ANIOS_INTERM = [a for a in ANIOS if ELECCIONES[a] == "intermedia"]
COLS_TASA = [f"tasa_{a}" for a in ANIOS]

# Esquema ESTÁNDAR (formato largo) que esperan los notebooks.
ESQUEMA = ["anio", "entidad", "distrito", "tipo_seccion", "sexo",
           "grupo_edad", "lista_nominal", "participantes"]
CLAVES_UNIDAD = ["entidad", "distrito", "tipo_seccion", "sexo", "grupo_edad"]

# --------------------------------------------------------------------------- #
# 2. Entidades y regiones (circunscripciones electorales)
# --------------------------------------------------------------------------- #
# Claves numéricas oficiales (orden alfabético INEGI/INE).
ENTIDADES_POR_CLAVE = {
    1: "AGUASCALIENTES", 2: "BAJA CALIFORNIA", 3: "BAJA CALIFORNIA SUR",
    4: "CAMPECHE", 5: "COAHUILA", 6: "COLIMA", 7: "CHIAPAS", 8: "CHIHUAHUA",
    9: "CIUDAD DE MEXICO", 10: "DURANGO", 11: "GUANAJUATO", 12: "GUERRERO",
    13: "HIDALGO", 14: "JALISCO", 15: "MEXICO", 16: "MICHOACAN", 17: "MORELOS",
    18: "NAYARIT", 19: "NUEVO LEON", 20: "OAXACA", 21: "PUEBLA", 22: "QUERETARO",
    23: "QUINTANA ROO", 24: "SAN LUIS POTOSI", 25: "SINALOA", 26: "SONORA",
    27: "TABASCO", 28: "TAMAULIPAS", 29: "TLAXCALA", 30: "VERACRUZ",
    31: "YUCATAN", 32: "ZACATECAS",
}

# Circunscripciones electorales (5 regiones). VERIFICA este mapeo contra la
# fuente oficial antes de publicar; puedes cambiarlo por otra regionalización
# (p. ej. norte/centro/sur) editando este diccionario.
_CIRC = {
    1: ["BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CHIHUAHUA", "DURANGO",
        "JALISCO", "NAYARIT", "SINALOA", "SONORA"],
    2: ["AGUASCALIENTES", "COAHUILA", "GUANAJUATO", "NUEVO LEON", "QUERETARO",
        "SAN LUIS POTOSI", "TAMAULIPAS", "ZACATECAS"],
    3: ["CAMPECHE", "CHIAPAS", "OAXACA", "QUINTANA ROO", "TABASCO",
        "VERACRUZ", "YUCATAN"],
    4: ["CIUDAD DE MEXICO", "GUERRERO", "MORELOS", "PUEBLA", "TLAXCALA"],
    5: ["COLIMA", "HIDALGO", "MEXICO", "MICHOACAN"],
}
REGION_POR_ENTIDAD = {e: f"Circ. {c}" for c, es in _CIRC.items() for e in es}

_ALIAS_ENTIDAD = {
    "DISTRITO FEDERAL": "CIUDAD DE MEXICO", "CDMX": "CIUDAD DE MEXICO",
    "ESTADO DE MEXICO": "MEXICO", "COAHUILA DE ZARAGOZA": "COAHUILA",
    "MICHOACAN DE OCAMPO": "MICHOACAN",
    "VERACRUZ DE IGNACIO DE LA LLAVE": "VERACRUZ",
}


def _norm(texto) -> str:
    """Mayúsculas, sin acentos y sin espacios repetidos."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def normalizar_entidad(x) -> str:
    """Convierte clave numérica (9, '09', 9.0) o nombre a un nombre estándar."""
    try:
        return ENTIDADES_POR_CLAVE[int(float(x))]
    except (ValueError, KeyError, TypeError):
        pass
    n = _norm(x)
    return _ALIAS_ENTIDAD.get(n, n)


def normalizar_sexo(x) -> str:
    n = _norm(x)
    if n in {"H", "HOMBRE", "HOMBRES", "MASCULINO"}:
        return "Hombres"
    if n in {"M", "MUJER", "MUJERES", "FEMENINO"}:
        return "Mujeres"
    return n.title()


# --------------------------------------------------------------------------- #
# 3. Grupos de edad
# --------------------------------------------------------------------------- #
def edad_inferior(grupo) -> float:
    """'20-24' -> 20 ; '65+' -> 65 ; '80 y más' -> 80 ; sin número -> NaN."""
    m = re.search(r"\d+", str(grupo))
    return float(m.group()) if m else np.nan


def ciclo_vida(edad_inf: float) -> str:
    """Agrupa edades en 4 etapas de vida (útil para nombrar perfiles)."""
    if np.isnan(edad_inf):
        return "Sin dato"
    if edad_inf < 30:
        return "Jóvenes (18-29)"
    if edad_inf < 50:
        return "Adultos (30-49)"
    if edad_inf < 65:
        return "Mediana edad (50-64)"
    return "Mayores (65+)"


ORDEN_CICLO = ["Jóvenes (18-29)", "Adultos (30-49)",
               "Mediana edad (50-64)", "Mayores (65+)"]


def orden_grupos_edad(serie) -> list:
    """Devuelve los grupos de edad únicos ordenados de menor a mayor edad."""
    return sorted(pd.unique(serie), key=lambda g: (edad_inferior(g), str(g)))


# --------------------------------------------------------------------------- #
# 4. Carga y limpieza
# --------------------------------------------------------------------------- #
def cargar_datos_crudos(ruta, column_map: dict | None = None, hoja=0, **kwargs) -> pd.DataFrame:
    """
    Lee CSV/XLSX, renombra columnas con `column_map` y valida el esquema.

    column_map : {"nombre en tu archivo": "nombre estándar"}; ver `ESQUEMA`.
    """
    ruta = Path(ruta)
    if ruta.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(ruta, sheet_name=hoja, **kwargs)
    else:
        try:
            df = pd.read_csv(ruta, encoding="utf-8", **kwargs)
        except UnicodeDecodeError:
            df = pd.read_csv(ruta, encoding="latin-1", **kwargs)
    if column_map:
        df = df.rename(columns=column_map)
    faltan = [c for c in ESQUEMA if c not in df.columns]
    if faltan:
        raise ValueError(
            f"Faltan columnas del esquema estándar: {faltan}.\n"
            f"Columnas encontradas en tu archivo: {list(df.columns)}\n"
            "Completa COLUMN_MAP en el notebook 01 para renombrarlas."
        )
    return df[ESQUEMA].copy()


def limpiar_datos(df: pd.DataFrame):
    """
    Normaliza categorías, fuerza tipos numéricos y descarta filas inválidas.
    Devuelve (df_limpio, reporte) donde `reporte` cuenta lo que se descartó.
    """
    df = df.copy()
    reporte = {"filas_iniciales": len(df)}

    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    for c in ("lista_nominal", "participantes"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    antes = len(df)
    df = df.dropna(subset=["anio", "lista_nominal", "participantes"])
    reporte["descartadas_por_nulos_numericos"] = antes - len(df)

    antes = len(df)
    df = df[df["lista_nominal"] > 0]
    reporte["descartadas_lista_nominal_<=0"] = antes - len(df)

    antes = len(df)
    df = df[(df["participantes"] >= 0) & (df["participantes"] <= df["lista_nominal"])]
    reporte["descartadas_participantes_fuera_de_rango"] = antes - len(df)

    df["anio"] = df["anio"].astype(int)
    antes = len(df)
    df = df[df["anio"].isin(ANIOS)]
    reporte["descartadas_anio_no_considerado"] = antes - len(df)

    df["entidad"] = df["entidad"].map(normalizar_entidad)
    df["sexo"] = df["sexo"].map(normalizar_sexo)
    df["tipo_seccion"] = df["tipo_seccion"].fillna("Sin dato").astype(str).str.strip().str.title()
    df["distrito"] = df["distrito"].astype(str).str.strip()
    df["grupo_edad"] = df["grupo_edad"].astype(str).str.strip()

    reporte["filas_exactas_duplicadas (solo aviso)"] = int(df.duplicated().sum())
    reporte["filas_finales"] = len(df)
    return df.reset_index(drop=True), reporte


# --------------------------------------------------------------------------- #
# 5. Datos sintéticos (SOLO para probar el pipeline)
# --------------------------------------------------------------------------- #
def generar_datos_sinteticos(n_distritos: int = 300, seed: int = SEED) -> pd.DataFrame:
    """
    Simula una base con el esquema estándar. Se generan 5 "arquetipos" latentes
    de participación y se asignan a cada segmento según edad y tipo de sección.

    ⚠️ NO son datos reales: sirven únicamente para verificar que los notebooks
    corren de principio a fin. Los resultados con estos datos NO se reportan.
    """
    rng = np.random.default_rng(seed)
    entidades = list(ENTIDADES_POR_CLAVE.values())
    pesos = rng.dirichlet(np.ones(len(entidades)) * 3)
    cuentas = 1 + rng.multinomial(n_distritos - len(entidades), pesos)
    distritos = [(e, f"{i + 1:02d}-{j + 1:02d}")
                 for i, (e, c) in enumerate(zip(entidades, cuentas)) for j in range(c)]

    tipos = ["Urbana", "Mixta", "Rural"]
    sexos = ["Hombres", "Mujeres"]
    grupos = ["18-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
              "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]

    filas = [(e, d, t, s, g) for (e, d), t, s, g in product(distritos, tipos, sexos, grupos)]
    u = pd.DataFrame(filas, columns=CLAVES_UNIDAD)
    edad = u["grupo_edad"].map(edad_inferior).to_numpy()
    rural = (u["tipo_seccion"] == "Rural").to_numpy()
    urbana = (u["tipo_seccion"] == "Urbana").to_numpy()

    # Arquetipos: 0 alta constante | 1 presidencial | 2 baja | 3 creciente | 4 decreciente
    base = np.array([
        [.55, .75, .58, .76, .62, .74],
        [.35, .68, .37, .68, .42, .66],
        [.28, .45, .30, .47, .36, .50],
        [.30, .50, .38, .58, .50, .65],
        [.60, .70, .52, .62, .46, .52],
    ])
    logits = np.column_stack([
        0.06 * (edad - 45) + 0.3 * rural,
        0.5 - 0.01 * np.abs(edad - 35),
        -0.04 * (edad - 30) + 0.3 * urbana,
        0.3 - 0.03 * np.abs(edad - 27),
        0.03 * (edad - 60) - 0.5,
    ]) + rng.normal(0, 0.5, size=(len(u), 5))
    p = np.exp(logits - logits.max(1, keepdims=True))
    p /= p.sum(1, keepdims=True)
    arq = np.array([rng.choice(5, p=pi) for pi in p])

    efecto_dist = pd.Series(rng.normal(0, 0.02, len(distritos)),
                            index=[d for _, d in distritos])
    shift = u["distrito"].map(efecto_dist).to_numpy()[:, None]
    tasa = np.clip(base[arq] + shift + rng.normal(0, 0.03, (len(u), len(ANIOS))), 0.02, 0.95)
    ln0 = np.maximum(30, rng.lognormal(mean=6.0, sigma=0.6, size=len(u)))

    salida = []
    for i, a in enumerate(ANIOS):
        ln = np.round(ln0 * (1 + 0.03 * i)).astype(int)
        part = rng.binomial(ln, tasa[:, i])
        d = u.copy()
        d["anio"], d["lista_nominal"], d["participantes"] = a, ln, part
        salida.append(d)
    return pd.concat(salida, ignore_index=True)[ESQUEMA]


# --------------------------------------------------------------------------- #
# 6. Construcción de la matriz de unidades
# --------------------------------------------------------------------------- #
def construir_unidades(df: pd.DataFrame, min_lista: float = 30, max_faltantes: int = 2):
    """
    Pasa del formato largo (una fila por segmento y elección) al formato ancho
    (una fila por segmento, una columna por elección) y crea variables derivadas.

    Parámetros
    ----------
    min_lista     : se descartan segmentos con lista nominal media < min_lista
                    (tasas de segmentos diminutos son ruido: 3 de 5 = 60 %).
    max_faltantes : máximo de elecciones sin dato permitidas por segmento;
                    las faltantes restantes se imputan con la mediana de su
                    (grupo_edad, sexo).

    Devuelve (unidades, info) con info = conteos de lo descartado/imputado.
    """
    # 1) Agrega por segmento y elección (si la base viene a nivel sección,
    #    aquí se suma hasta distrito; si ya viene a distrito, no cambia nada).
    g = (df.groupby(CLAVES_UNIDAD + ["anio"], as_index=False)
           [["lista_nominal", "participantes"]].sum())
    g["tasa"] = g["participantes"] / g["lista_nominal"]

    # 2) Formato ancho: una columna de tasa por elección.
    ancho = g.pivot(index=CLAVES_UNIDAD, columns="anio", values="tasa").reindex(columns=ANIOS)
    ancho.columns = COLS_TASA
    ln_media = (g.pivot(index=CLAVES_UNIDAD, columns="anio", values="lista_nominal")
                  .reindex(columns=ANIOS).mean(axis=1).rename("ln_media"))
    u = ancho.join(ln_media)
    info = {"segmentos_iniciales": len(u)}

    # 3) Filtros de calidad.
    u = u[u["ln_media"] >= min_lista]
    info["tras_filtro_lista_nominal"] = len(u)
    u = u[u[COLS_TASA].isna().sum(axis=1) <= max_faltantes]
    info["tras_filtro_faltantes"] = len(u)

    # 4) Imputación de las pocas elecciones faltantes.
    info["celdas_imputadas"] = int(u[COLS_TASA].isna().sum().sum())
    u = u.reset_index()
    for c in COLS_TASA:
        med = u.groupby(["grupo_edad", "sexo"])[c].transform("median")
        u[c] = u[c].fillna(med).fillna(u[c].median())

    # 5) Variables derivadas del historial (sirven para interpretar).
    Y = u[COLS_TASA].to_numpy()
    xc = np.arange(len(ANIOS)) - (len(ANIOS) - 1) / 2
    u["tasa_media"] = Y.mean(axis=1)
    u["tasa_pres"] = u[[f"tasa_{a}" for a in ANIOS_PRES]].mean(axis=1)
    u["tasa_interm"] = u[[f"tasa_{a}" for a in ANIOS_INTERM]].mean(axis=1)
    u["brecha_pres_interm"] = u["tasa_pres"] - u["tasa_interm"]
    u["volatilidad"] = Y.std(axis=1)
    u["tendencia"] = ((Y - Y.mean(1, keepdims=True)) * xc).sum(1) / (xc ** 2).sum()

    # 6) Variables de caracterización.
    u["edad_inferior"] = u["grupo_edad"].map(edad_inferior)
    u["ciclo_vida"] = u["edad_inferior"].map(ciclo_vida)
    u["region"] = u["entidad"].map(REGION_POR_ENTIDAD).fillna("Sin región")
    return u, info


# --------------------------------------------------------------------------- #
# 7. Utilidades de análisis
# --------------------------------------------------------------------------- #
def media_ponderada(df: pd.DataFrame, cols, peso: str, por: str) -> pd.DataFrame:
    """Media de `cols` ponderada por `peso`, agrupando por la columna `por`."""
    num = df[cols].mul(df[peso], axis=0).groupby(df[por]).sum()
    den = df[peso].groupby(df[por]).sum()
    return num.div(den, axis=0)
