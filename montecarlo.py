"""
montecarlo.py
-------------
Ejecuta N réplicas independientes de la simulación DES para estimar
métricas de desempeño del sistema de colas de TechClassUC mediante
simulación de Montecarlo.

Funciones principales
---------------------
correr_replicas()          : ejecuta N réplicas y agrega resultados.
calcular_n_minimo()        : número mínimo de réplicas para error ≤ 5%.
resumen_estadistico()      : media, std, IC al 95% para cada métrica.
"""

import math
import statistics
from typing import Optional

from simulacion_des import correr_una_replica


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def correr_replicas(
    N: int,
    lam: float,
    mu: float,
    c: int,
    t_sim: float = 480.0,
    t_warm: float = 60.0,
    semilla_base: int = 42,
    usar_prioridad: bool = False,
) -> dict:
    """
    Ejecuta N réplicas independientes de la simulación DES.

    Cada réplica usa semilla = semilla_base + i para garantizar
    independencia y reproducibilidad.

    Parameters
    ----------
    N            : número de réplicas.
    lam          : tasa de llegada (clientes/hora).
    mu           : tasa de servicio (clientes/hora por técnico).
    c            : número de técnicos.
    t_sim        : duración de la simulación (minutos).
    t_warm       : período de calentamiento (minutos).
    semilla_base : semilla inicial; réplica i usa semilla_base + i.
    usar_prioridad: habilitar cola con prioridad.

    Returns
    -------
    dict con:
        replicas   : lista de dicts con resultados por réplica.
        resumen    : estadísticas agregadas (media, std, IC 95%).
        wq_todas   : lista plana de todos los Wq individuales.
        n_minimo   : réplicas mínimas para error relativo ≤ 5%.
    """
    _validar_parametros(N, lam, mu, c, t_sim, t_warm)

    replicas = []
    wq_todas = []
    ws_todas = []

    for i in range(N):
        resultado = correr_una_replica(
            lam=lam, mu=mu, c=c,
            t_sim=t_sim, t_warm=t_warm,
            semilla=semilla_base + i,
            usar_prioridad=usar_prioridad,
        )
        replicas.append(resultado)
        wq_todas.extend(resultado["wq_lista"])
        ws_todas.extend(resultado["ws_lista"])

    resumen = resumen_estadistico(replicas)
    n_min = calcular_n_minimo(replicas)

    return {
        "replicas": replicas,
        "resumen": resumen,
        "wq_todas": wq_todas,
        "ws_todas": ws_todas,
        "n_minimo": n_min,
    }


def _validar_parametros(
    N: int,
    lam: float,
    mu: float,
    c: int,
    t_sim: float,
    t_warm: float,
) -> None:
    """Valida que la simulacion tenga parametros positivos y estables."""
    numericos = {
        "N": N,
        "lam": lam,
        "mu": mu,
        "c": c,
        "t_sim": t_sim,
        "t_warm": t_warm,
    }

    for nombre, valor in numericos.items():
        try:
            valor_num = float(valor)
        except (TypeError, ValueError):
            raise ValueError(f"{nombre} debe ser un numero valido") from None

        if not math.isfinite(valor_num):
            raise ValueError(f"{nombre} debe ser un numero finito")

    if N <= 0:
        raise ValueError("N debe ser mayor que cero")
    if lam <= 0:
        raise ValueError("lam debe ser mayor que cero")
    if mu <= 0:
        raise ValueError("mu debe ser mayor que cero")
    if c <= 0:
        raise ValueError("c debe ser mayor que cero")
    if t_sim <= 0:
        raise ValueError("t_sim debe ser mayor que cero")
    if t_warm < 0:
        raise ValueError("t_warm no puede ser negativo")
    if t_warm >= t_sim:
        raise ValueError("t_warm debe ser menor que t_sim")

    rho = lam / (c * mu)
    if rho >= 1:
        raise ValueError(f"Sistema inestable: rho = {rho:.3f}. Debe cumplirse lam < c*mu")


# ---------------------------------------------------------------------------
# Estadísticas agregadas
# ---------------------------------------------------------------------------

def resumen_estadistico(replicas: list[dict]) -> dict:
    """
    Calcula media, desviación estándar e intervalo de confianza al 95%
    para cada métrica a partir de las N réplicas.

    Parameters
    ----------
    replicas : lista de resultados de correr_una_replica().

    Returns
    -------
    dict con sub-dicts por métrica, cada uno con:
        media, std, ic_inferior, ic_superior, n
    """
    metricas = ["wq_promedio", "ws_promedio", "lq_promedio", "rho", "n_clientes"]
    resumen = {}

    for m in metricas:
        valores = [r[m] for r in replicas]
        n = len(valores)
        media = statistics.mean(valores)
        std = statistics.stdev(valores) if n > 1 else 0.0
        t_95 = _t_student_95(n - 1)
        margen = t_95 * std / math.sqrt(n)

        resumen[m] = {
            "media": media,
            "std": std,
            "ic_inferior": media - margen,
            "ic_superior": media + margen,
            "n": n,
        }

    return resumen


# ---------------------------------------------------------------------------
# Número mínimo de réplicas
# ---------------------------------------------------------------------------

def calcular_n_minimo(replicas: list[dict], error_rel: float = 0.05) -> int:
    """
    Estima el número mínimo de réplicas N* para que el error relativo
    del estimador de Wq sea ≤ error_rel (default 5%).

    Fórmula: N* = (t_{α/2, N-1} · s / (ε · x̄))²

    Parameters
    ----------
    replicas  : lista de dicts de resultados.
    error_rel : error relativo máximo permitido (fracción, default 0.05).

    Returns
    -------
    int : número mínimo de réplicas recomendado.
    """
    wq_vals = [r["wq_promedio"] for r in replicas]
    n = len(wq_vals)
    if n < 2:
        return n

    media = statistics.mean(wq_vals)
    std = statistics.stdev(wq_vals)

    if media == 0:
        return n

    t_95 = _t_student_95(n - 1)
    n_min = math.ceil((t_95 * std / (error_rel * media)) ** 2)
    return max(n_min, 1)


# ---------------------------------------------------------------------------
# Helper: valor crítico t de Student al 95% (two-tail)
# ---------------------------------------------------------------------------

def _t_student_95(df: int) -> float:
    """
    Aproxima el cuantil t_{0.025, df} mediante tabla abreviada.
    Para df ≥ 120 usa z = 1.96.
    """
    tabla = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        25: 2.060, 29: 2.045, 30: 2.042, 40: 2.021, 60: 2.000,
        120: 1.980,
    }
    if df <= 0:
        return 1.96
    if df in tabla:
        return tabla[df]
    # Interpolación lineal simple entre las claves más cercanas
    claves = sorted(tabla.keys())
    for i in range(len(claves) - 1):
        if claves[i] <= df <= claves[i + 1]:
            k0, k1 = claves[i], claves[i + 1]
            frac = (df - k0) / (k1 - k0)
            return tabla[k0] + frac * (tabla[k1] - tabla[k0])
    return 1.96
