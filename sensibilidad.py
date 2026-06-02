"""
sensibilidad.py
---------------
Realiza el análisis de sensibilidad del sistema TechClassUC variando
sistemáticamente la tasa de llegada λ y el número de servidores c.

Genera tablas de resultados con Wq, Lq y ρ para cada combinación (c, λ).
"""

import numpy as np
from montecarlo import correr_replicas


# ---------------------------------------------------------------------------
# Barrido de parámetros
# ---------------------------------------------------------------------------

def analisis_sensibilidad(
    mu: float = 4.0,
    t_sim: float = 1440,
    t_warm: float = 180,
    N: int = 100,
    semilla_base: int = 42,
    c_valores: list | None = None,
    lam_valores: list | None = None,
) -> dict:
    """
    Ejecuta la simulación de Montecarlo para cada combinación (c, λ).

    Parameters
    ----------
    mu           : tasa de servicio (clientes/hora por técnico).
    t_sim        : duración de la simulación (minutos).
    t_warm       : período de calentamiento (minutos).
    N            : número de réplicas por combinación.
    semilla_base : semilla base para la simulación.
    c_valores    : lista de valores de c a evaluar.
    lam_valores  : lista de valores de λ a evaluar.

    Returns
    -------
    dict con:
        c_valores   : array de c evaluados.
        lam_valores : array de λ evaluados.
        wq_matrix   : matriz Wq[i_c, i_lam] en minutos.
        lq_matrix   : matriz Lq[i_c, i_lam].
        rho_matrix  : matriz ρ[i_c, i_lam].
        resultados  : lista de dicts con todos los detalles.
    """
    if c_valores is None:
        c_valores = [2, 3, 4, 5]
    if lam_valores is None:
        lam_valores = [8, 10, 12, 14, 16]

    c_arr = np.array(c_valores, dtype=int)
    lam_arr = np.array(lam_valores, dtype=float)

    wq_matrix  = np.zeros((len(c_arr), len(lam_arr)))
    lq_matrix  = np.zeros_like(wq_matrix)
    rho_matrix = np.zeros_like(wq_matrix)

    resultados = []

    for i, c in enumerate(c_arr):
        for j, lam in enumerate(lam_arr):
            rho_check = lam / (c * mu)
            if rho_check >= 1.0:
                # Sistema inestable → marcar con NaN
                wq_matrix[i, j] = np.nan
                lq_matrix[i, j] = np.nan
                rho_matrix[i, j] = rho_check
                resultados.append({
                    "c": int(c), "lam": float(lam),
                    "rho": rho_check, "estable": False,
                    "wq": np.nan, "lq": np.nan,
                })
                continue

            res = correr_replicas(
                N=N, lam=float(lam), mu=mu, c=int(c),
                t_sim=t_sim, t_warm=t_warm,
                semilla_base=semilla_base,
            )
            wq = res["resumen"]["wq_promedio"]["media"]
            lq = res["resumen"]["lq_promedio"]["media"]
            rho_sim = res["resumen"]["rho"]["media"]

            wq_matrix[i, j]  = wq
            lq_matrix[i, j]  = lq
            rho_matrix[i, j] = rho_sim

            resultados.append({
                "c": int(c), "lam": float(lam),
                "rho": rho_sim, "estable": True,
                "wq": wq, "lq": lq,
                "ic_wq": res["resumen"]["wq_promedio"],
            })

    return {
        "c_valores": c_arr,
        "lam_valores": lam_arr,
        "wq_matrix": wq_matrix,
        "lq_matrix": lq_matrix,
        "rho_matrix": rho_matrix,
        "resultados": resultados,
    }


# ---------------------------------------------------------------------------
# Impresión de tabla de resultados
# ---------------------------------------------------------------------------

def imprimir_tabla_sensibilidad(sens: dict) -> None:
    """Imprime la tabla de Wq para cada combinación (c, λ)."""
    c_vals = sens["c_valores"]
    lam_vals = sens["lam_valores"]
    wq_mat = sens["wq_matrix"]

    print("\n" + "=" * 65)
    print("  ANÁLISIS DE SENSIBILIDAD — Wq promedio (minutos)")
    print("=" * 65)

    # Encabezado
    col_title = "c \\ λ"
    header = f"{col_title:>6}" + "".join(f"{lam:>10.1f}" for lam in lam_vals)
    print(header)
    print("-" * len(header))

    for i, c in enumerate(c_vals):
        fila = f"{c:>6}"
        for j in range(len(lam_vals)):
            val = wq_mat[i, j]
            fila += f"{'INESTABLE':>10}" if (val != val) else f"{val:>10.2f}"
        print(fila)
    print("=" * 65)
