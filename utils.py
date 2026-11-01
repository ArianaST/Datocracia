# -*- coding: utf-8 -*-
"""Funciones compartidas del flujo Datocracia 01–04.

Rutas, normalización de categorías, indicadores de participación y resúmenes
cuantitativos. Unidad: entidad × distrito de referencia × sexo × grupo de edad.
El modelo usa cuatro variables electorales; la demografía caracteriza los resultados.
"""
from __future__ import annotations

import re
import unicodedata
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
    """Agrupa los intervalos de edad en cuatro etapas para tablas de composición."""
    if np.isnan(edad_inf):
        return "Sin dato"
    if edad_inf < 30:
        return "Jóvenes (18-29)"
    if edad_inf < 51:
        return "Adultos (30-50)"
    if edad_inf < 67:
        return "Mediana edad (51-66)"
    return "Mayores (67+)"


ORDEN_CICLO = ["Jóvenes (18-29)", "Adultos (30-50)",
               "Mediana edad (51-66)", "Mayores (67+)"]


def orden_grupos_edad(serie) -> list:
    """Devuelve los grupos de edad únicos ordenados de menor a mayor edad."""
    return sorted(pd.unique(serie), key=lambda g: (edad_inferior(g), str(g)))



# Resúmenes e indicadores compartidos.
def media_ponderada(df: pd.DataFrame, cols, peso: str, por: str) -> pd.DataFrame:
    """Media de `cols` ponderada por `peso`, agrupando por la columna `por`."""
    num = df[cols].mul(df[peso], axis=0).groupby(df[por]).sum()
    den = df[peso].groupby(df[por]).sum()
    return num.div(den, axis=0)


# --------------------------------------------------------------------------- #
# 8. Diagnósticos compartidos: edad, ruido y dependencia (no cambian el universo)
# --------------------------------------------------------------------------- #
VERSION_VARIABLES = "variables_v9_trayectoria"
VERSION_MODELO = "kmeans_trayectoria_seis_2026"
VARIABLES_ACTUALES = ["participacion_media", "brecha_presidencial_intermedia",
                     "tendencia_general", "diferencia_tendencias"]
CURVATURAS = ["curvatura_intermedia", "curvatura_presidencial"]
VARIABLES_RELATIVAS = ["exceso_medio", "brecha_relativa", "tendencia_relativa",
                       "diferencia_tendencias_relativa", "pendiente_ols_relativa"]
CURVATURAS_REL = ["curvatura_intermedia_rel", "curvatura_presidencial_rel"]
VARIABLES_PARTICIPACION = ["participacion_media", "brecha_presidencial_intermedia", "cambio_reciente", "irregularidad_trayectoria"]
FEATURES_SETS = {"participacion": VARIABLES_PARTICIPACION}


UNIDADES_INDICADORES = {v: ("%" if v == "participacion_media" else
    "pp/año" if v in {"tendencia_general", "diferencia_tendencias", "tendencia_relativa", "diferencia_tendencias_relativa", "pendiente_ols_relativa"}
    else "pp") for v in VARIABLES_ACTUALES + CURVATURAS + VARIABLES_RELATIVAS + CURVATURAS_REL}
ETIQUETAS_INDICADORES = dict(zip(
    VARIABLES_ACTUALES + CURVATURAS + VARIABLES_RELATIVAS + CURVATURAS_REL,
    ["Participación media", "Brecha presidencial–intermedia", "Tendencia general",
     "Diferencia de tendencias", "Curvatura intermedia", "Curvatura presidencial",
     "Exceso medio respecto a edad y sexo", "Brecha relativa a edad y sexo",
     "Tendencia relativa a edad y sexo", "Diferencia de tendencias relativa a edad y sexo",
     "Pendiente OLS relativa a edad y sexo", "Curvatura intermedia relativa",
     "Curvatura presidencial relativa"]))


UNIDADES_INDICADORES.update({"cambio_reciente": "pp/año", "irregularidad_trayectoria": "pp"})
ETIQUETAS_INDICADORES.update({"cambio_reciente": "Cambio reciente", "irregularidad_trayectoria": "Irregularidad de trayectoria"})


def indicadores_trayectoria(tasas):
    """Tasas 0–1 en orden 2009…2024; crecimiento reciente y RMS residual en pp."""
    p = np.asarray(tasas, dtype=float) * 100
    tiempo = np.asarray(ANIOS, dtype=float) - np.mean(ANIOS)
    diseno = np.column_stack([np.ones(6), [0, 1, 0, 1, 0, 1], tiempo])
    residuos = p - p @ np.linalg.pinv(diseno).T @ diseno.T
    return {
        "cambio_reciente": ((p[:, 4]-p[:, 2])+(p[:, 5]-p[:, 3]))/12,
        "irregularidad_trayectoria": np.sqrt(np.mean(residuos**2, axis=1)),
    }


def ruta_set(carpeta, nombre, conjunto="actual"):
    """Actual conserva sus nombres; las otras representaciones usan sufijo."""
    p = Path(nombre)
    sufijo = "" if conjunto == "actual" else "_" + conjunto
    return Path(carpeta) / (p.stem + sufijo + p.suffix)


def indicadores_excesos(excesos_pp):
    x = np.asarray(excesos_pp, dtype=float)
    tiempo = np.asarray(ANIOS, dtype=float) - np.mean(ANIOS)
    return {"pendiente_ols_relativa": x @ tiempo / (tiempo @ tiempo),
            "exceso_medio": x.mean(axis=1),
            "brecha_relativa": x[:, [1, 3, 5]].mean(axis=1)-x[:, [0, 2, 4]].mean(axis=1),
            "tendencia_relativa": (x[:, 5]-x[:, 1]+x[:, 4]-x[:, 0])/24,
            "diferencia_tendencias_relativa": ((x[:, 5]-x[:, 1])-(x[:, 4]-x[:, 0]))/12,
            "curvatura_intermedia_rel": x[:, 4]-2*x[:, 2]+x[:, 0],
            "curvatura_presidencial_rel": x[:, 5]-2*x[:, 3]+x[:, 1]}


def agregar_benchmark_edad(todas, g, claves, anios=ANIOS):
    """Benchmark nacional por edad, sexo y año, solo con segmentos elegibles."""
    elegibles = todas.loc[todas.elegible_clustering, claves].drop_duplicates()
    fuente = g.merge(elegibles, on=claves, how="inner", validate="many_to_one")
    nacional = fuente.groupby(["grupo_edad", "sexo", "anio"], observed=True)[
        ["participantes", "denominador"]].sum()
    nacional["tasa_nac"] = nacional.participantes/nacional.denominador.where(nacional.denominador.gt(0))
    for a in anios:
        ref = nacional.xs(a, level="anio").tasa_nac
        todas[f"exceso_{a}"] = 100*(todas[f"tasa_{a}"]-ref.reindex(pd.MultiIndex.from_frame(todas[["grupo_edad", "sexo"]])).to_numpy())
    nombres = [f"exceso_{a}" for a in anios]
    for v, valores in indicadores_excesos(todas[nombres]).items():
        todas[v] = valores
    todas.loc[~todas.cobertura_completa, nombres + VARIABLES_RELATIVAS + CURVATURAS_REL] = np.nan
    # Identidad numérica, no prueba de independencia ni de ausencia de sesgo.
    e = todas.loc[todas.elegible_clustering]
    for a in anios:
        suma = (e[f"exceso_{a}"]*e[f"denominador_{a}"]).groupby([e.grupo_edad, e.sexo]).sum()
        masa = e[f"denominador_{a}"].groupby([e.grupo_edad, e.sexo]).sum()
        assert np.allclose(suma/masa, 0, atol=1e-9), "Benchmark/excesos incompatibles"
    return nacional.reset_index()


def eta2_ponderada(valores, grupos, pesos=None):
    y = np.asarray(valores, float)
    w = np.ones(len(y)) if pesos is None else np.asarray(pesos, float)
    ok = np.isfinite(y) & np.isfinite(w) & (w > 0)
    y, w, g = y[ok], w[ok], np.asarray(grupos)[ok]
    if not len(y): return np.nan
    mu = np.average(y, weights=w); total = np.sum(w*(y-mu)**2)
    entre = sum(np.sum(w[g == c])*(np.average(y[g == c], weights=w[g == c])-mu)**2 for c in np.unique(g))
    return float(entre/total) if total > 0 else 0.


def asociaciones_particion(labels, grupos, pesos=None):
    """ARI estándar sin pesos; NMI y V también se calculan con masas de LN.
    El ARI de las filas ponderadas queda vacío porque no se define esa extensión.
    """
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    a, ai = np.unique(np.asarray(labels).astype(str), return_inverse=True)
    b, bi = np.unique(np.asarray(grupos).astype(str), return_inverse=True)
    w = np.ones(len(ai)) if pesos is None else np.asarray(pesos, float)
    tabla = np.zeros((len(a), len(b)))
    np.add.at(tabla, (ai, bi), w)
    n = tabla.sum()
    pr, pc = tabla.sum(1), tabla.sum(0)
    esperado = np.outer(pr, pc)/n
    chi2 = np.sum(np.divide((tabla-esperado)**2, esperado, out=np.zeros_like(tabla), where=esperado > 0))
    v = np.sqrt(chi2/(n*min(len(a)-1, len(b)-1))) if min(len(a),len(b)) > 1 else np.nan
    p = tabla/n; pa, pb = pr/n, pc/n
    exp = np.outer(pa, pb); nz = p > 0
    info = np.sum(p[nz]*np.log(p[nz]/exp[nz]))
    ha = -np.sum(pa[pa > 0]*np.log(pa[pa > 0]))
    hb = -np.sum(pb[pb > 0]*np.log(pb[pb > 0]))
    nmi = 2*info/(ha+hb) if ha+hb > 0 else 1.
    return dict(ari=adjusted_rand_score(labels, grupos) if pesos is None else np.nan,
                nmi=normalized_mutual_info_score(labels, grupos) if pesos is None else nmi,
                cramer_v=v)


def asociaciones_factores(datos, labels):
    filas = []
    for peso in ["segmentos", "ln_media"]:
        w = None if peso == "segmentos" else datos.ln_media.to_numpy(float)
        for f in ["grupo_edad", "ciclo_vida", "region", "entidad", "sexo"]:
            filas.append(dict(factor=f, peso=peso, **asociaciones_particion(labels, datos[f], w)))
    return pd.DataFrame(filas)


def heterogeneidad_perfiles(datos, labels, variables):
    """Eta2 global y SD intra sin pesos, sobre el conjunto de ajuste."""
    filas, intra = [], []
    for v in variables:
        y = datos[v].to_numpy(float)
        eta = eta2_ponderada(y, labels)
        filas.append(dict(variable=v, eta2_entre_perfiles=eta, proporcion_intra=1-eta))
        for c in np.unique(labels):
            intra.append(dict(cluster=int(c), variable=v,
                sd_intra=float(np.std(y[np.asarray(labels) == c], ddof=0)),
                eta2_entre_perfiles=eta))
    return pd.DataFrame(filas), pd.DataFrame(intra)


def estandarizar_trayectorias_edad(datos, anios=ANIOS):
    """Estándar fijo: LN media de cada edad en toda la base.
    Sin imputar: estándar completo = NaN si falta una edad. Se ofrece además una
    comparación secundaria sobre soporte común a todos los perfiles y años.
    """
    perfiles = sorted(datos.cluster.unique())
    edades = orden_grupos_edad(datos.grupo_edad)
    masa = datos.groupby("grupo_edad", observed=True).ln_media.sum().reindex(edades)
    pesos = masa/masa.sum()
    tasas, cobertura = {}, []
    comunes = set(edades)
    for a in anios:
        t = datos.groupby(["cluster","grupo_edad"], observed=True)[
            [f"participantes_{a}",f"denominador_{a}"]].sum()
        p = (t[f"participantes_{a}"]/t[f"denominador_{a}"].where(t[f"denominador_{a}"].gt(0))).unstack("grupo_edad")
        p = p.reindex(index=perfiles, columns=edades)
        tasas[a] = p
        comunes &= set(p.columns[p.notna().all(axis=0)])
        for c in perfiles:
            disponibles = p.loc[c].notna()
            cobertura.append(dict(cluster=c, anio=a,
                peso_edad_cubierto=float(pesos[disponibles].sum()),
                edades_ausentes=";".join(pesos.index[~disponibles]), cobertura_completa=bool(disponibles.all())))
    completa = pd.DataFrame(index=pd.Index(perfiles,name="cluster"))
    comun = completa.copy()
    comunes = [e for e in edades if e in comunes]
    for a in anios:
        completa[f"tasa_{a}"] = (tasas[a]*pesos).sum(axis=1, min_count=len(edades))
        comun[f"tasa_{a}"] = ((tasas[a][comunes]*(pesos[comunes]/pesos[comunes].sum())).sum(axis=1)
                              if comunes else np.nan)
    return completa, comun, pd.DataFrame(cobertura), pesos, comunes


