"""
analitico.py
------------
Implementa las fórmulas cerradas del modelo M/M/c para calcular las
métricas teóricas del sistema de colas de TechClassUC.

Funciones
---------
calcular_mmc()              : métricas analíticas completas del modelo M/M/c.
comparar_con_simulacion()   : tabla de comparación teoría vs simulación.
"""

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Modelo M/M/c — métricas analíticas
# ---------------------------------------------------------------------------

def calcular_mmc(lam: float, mu: float, c: int) -> Optional[dict]:
    """
    Calcula las métricas del modelo M/M/c a partir de los parámetros base.

    Parameters
    ----------
    lam : tasa de llegada (clientes/hora).
    mu  : tasa de servicio por servidor (clientes/hora).
    c   : número de servidores en paralelo.

    Returns
    -------
    dict con métricas o None si el sistema es inestable (ρ ≥ 1).

    Métricas retornadas
    -------------------
    rho     : factor de utilización por servidor = λ/(c·μ).
    P0      : probabilidad de sistema vacío.
    Lq      : número promedio de clientes en cola.
    Wq      : tiempo promedio en cola (minutos).
    L       : número promedio de clientes en sistema.
    W       : tiempo promedio en sistema (minutos).
    """
    rho = lam / (c * mu)
    if rho >= 1:
        return None  # Sistema inestable

    a = lam / mu  # oferta total = ρ_total antes de dividir entre c

    # P0 — probabilidad de sistema vacío
    # Suma para n = 0 … c-1 de (a^n / n!) + a^c / (c! * (1 - rho))
    suma = sum((a ** n) / math.factorial(n) for n in range(c))
    termino_c = (a ** c) / (math.factorial(c) * (1 - rho))
    P0 = 1.0 / (suma + termino_c)

    # Lq — clientes promedio en cola
    Lq = (P0 * (a ** c) * rho) / (math.factorial(c) * (1 - rho) ** 2)

    # Wq — tiempo promedio en cola (horas) → convertir a minutos
    Wq_h = Lq / lam
    Wq_min = Wq_h * 60.0

    # L — clientes promedio en sistema
    L = Lq + a  # L = Lq + λ/μ

    # W — tiempo promedio en sistema (minutos)
    W_h = L / lam
    W_min = W_h * 60.0

    # Wq en minutos para la tabla
    Ws_min = W_min

    return {
        "rho": rho,
        "P0": P0,
        "Lq": Lq,
        "Wq": Wq_min,       # minutos
        "L": L,
        "W": Ws_min,        # minutos
    }


# ---------------------------------------------------------------------------
# Comparación teoría vs simulación
# ---------------------------------------------------------------------------

def comparar_con_simulacion(
    lam: float,
    mu: float,
    c: int,
    sim_resumen: dict,
) -> list[dict]:
    """
    Genera una tabla comparativa entre valores analíticos (M/M/c) y
    los estimados por la simulación de Montecarlo.

    Parameters
    ----------
    lam         : tasa de llegada (clientes/hora).
    mu          : tasa de servicio (clientes/hora por técnico).
    c           : número de técnicos.
    sim_resumen : dict retornado por montecarlo.resumen_estadistico().

    Returns
    -------
    list[dict] con filas de la tabla; cada fila tiene:
        metrica, valor_teorico, valor_simulado, error_relativo_pct.
    """
    teorico = calcular_mmc(lam, mu, c)
    if teorico is None:
        raise ValueError(f"Sistema inestable: ρ = {lam/(c*mu):.3f} ≥ 1")

    # Mapeo: nombre en teorico → nombre en sim_resumen
    mapeo = {
        "Wq": "wq_promedio",
        "W": "ws_promedio",
        "Lq": "lq_promedio",
        "rho": "rho",
    }

    tabla = []
    for nombre_teo, nombre_sim in mapeo.items():
        v_teo = teorico[nombre_teo]
        v_sim = sim_resumen[nombre_sim]["media"]
        if v_teo != 0:
            err_pct = abs(v_sim - v_teo) / abs(v_teo) * 100.0
        else:
            err_pct = 0.0

        tabla.append({
            "metrica": nombre_teo,
            "valor_teorico": v_teo,
            "valor_simulado": v_sim,
            "error_relativo_pct": err_pct,
        })

    return tabla


# ---------------------------------------------------------------------------
# Impresión de resultados analíticos
# ---------------------------------------------------------------------------

def imprimir_resultados_analiticos(lam: float, mu: float, c: int) -> None:
    """Imprime en consola las métricas analíticas del modelo M/M/c."""
    res = calcular_mmc(lam, mu, c)
    if res is None:
        print(f"⚠️  Sistema INESTABLE (ρ = {lam/(c*mu):.3f} ≥ 1). "
              "Aumenta c o reduce λ.")
        return

    print("\n" + "=" * 50)
    print("  RESULTADOS ANALÍTICOS  M/M/c")
    print("=" * 50)
    print(f"  λ = {lam} cl/h  |  μ = {mu} cl/h  |  c = {c} técnicos")
    print(f"  ρ  (utilización)   = {res['rho']:.4f}")
    print(f"  P₀ (sistema vacío) = {res['P0']:.4f}")
    print(f"  Lq (cola)          = {res['Lq']:.4f} clientes")
    print(f"  Wq (espera)        = {res['Wq']:.4f} min")
    print(f"  L  (sistema)       = {res['L']:.4f} clientes")
    print(f"  W  (sistema total) = {res['W']:.4f} min")
    print("=" * 50)
