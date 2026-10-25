# -*- coding: utf-8 -*-
"""
generar_tablas_latex.py
-----------------------
Convierte los CSV que producen los notebooks (../outputs/tablas) en archivos .tex
que main.tex incluye automáticamente. Así no copias números a mano.

Uso (desde la carpeta documento/):
    python generar_tablas_latex.py

Genera:
    tablas/tabla_k.tex            métricas de selección de k (k = 2..10)
    tablas/tabla_perfiles.tex     trayectoria de participación por perfil
    valores_perfiles.tex          macros \valor{perfil}{campo} usadas en main.tex
Solo requiere pandas.
"""
from pathlib import Path
import pandas as pd

AQUI = Path(__file__).resolve().parent
TAB = AQUI.parent / "outputs" / "tablas"
(AQUI / "tablas").mkdir(exist_ok=True)


def fmt(x, d=2):
    return f"{x:.{d}f}"


# ------------------------------ Tabla de selección de k ------------------------------
m = pd.read_csv(TAB / "metricas_seleccion_k.csv")
filas = []
for _, r in m.iterrows():
    k = int(r["k"])
    marca = r"\rowcolor{purple!8} " if 4 <= k <= 6 else ""
    filas.append(
        f"{marca}{k} & {fmt(r['silueta'], 3)} & {r['calinski_harabasz']:,.0f} & {fmt(r['davies_bouldin'], 3)} & "
        f"{r['bic_gmm']:,.0f} & {fmt(r['tam_min_pct'], 1)} & {fmt(r['ari_estabilidad'], 3)} \\\\"
    )
tabla_k = (
    "\\begin{tabular}{@{}rrrrrrr@{}}\n\\toprule\n"
    "$k$ & Silueta $\\uparrow$ & C-H $\\uparrow$ & D-B $\\downarrow$ & BIC (GMM) $\\downarrow$ & "
    "Grupo menor (\\%) & ARI boot. $\\uparrow$ \\\\\n\\midrule\n"
    + "\n".join(filas) + "\n\\bottomrule\n\\end{tabular}\n"
)
(AQUI / "tablas" / "tabla_k.tex").write_text(tabla_k, encoding="utf-8")

# ------------------------------ Tabla de perfiles ------------------------------
p = pd.read_csv(TAB / "perfil_resumen.csv")
anios = [c for c in p.columns if c.startswith("tasa_20")]
cab = " & ".join(["Perfil", "\\% lista"] + [c.split("_")[1] for c in anios])
filas = []
for _, r in p.iterrows():
    filas.append(" & ".join([str(int(r["cluster"])), fmt(r["%_lista_nominal"], 1)] +
                            [fmt(r[c] * 100, 1) for c in anios]) + " \\\\")
tabla_p = (
    "\\begin{tabular}{@{}rr" + "r" * len(anios) + "@{}}\n\\toprule\n" + cab + " \\\\\n\\midrule\n"
    + "\n".join(filas) + "\n\\bottomrule\n\\end{tabular}\n"
)
(AQUI / "tablas" / "tabla_perfiles.tex").write_text(tabla_p, encoding="utf-8")

# ------------------------------ Macros \valor{perfil}{campo} ------------------------------
lineas = ["% Archivo generado automáticamente por generar_tablas_latex.py; no editar a mano."]
for _, r in p.iterrows():
    c = int(r["cluster"])
    vals = {
        "n": f"{int(r['n_segmentos']):,}".replace(",", "\\,"),
        "pct": fmt(r["%_lista_nominal"], 1),
        "media": fmt(r["tasa_media"] * 100, 1),
        "pres": fmt(r["tasa_pres"] * 100, 1),
        "interm": fmt(r["tasa_interm"] * 100, 1),
        "brecha": fmt(r["brecha_pres_interm"] * 100, 1),
        "tend": f"{r['tendencia'] * 100:+.1f}",
        "vol": fmt(r["volatilidad"] * 100, 1),
    }
    for campo, v in vals.items():
        lineas.append(f"\\expandafter\\gdef\\csname val@{c}@{campo}\\endcsname{{{v}}}")
(AQUI / "valores_perfiles.tex").write_text("\n".join(lineas) + "\n", encoding="utf-8")
print("Listo: tablas/tabla_k.tex, tablas/tabla_perfiles.tex, valores_perfiles.tex")
