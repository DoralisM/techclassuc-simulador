"""
visualizacion.py
----------------
Genera todas las gráficas Matplotlib requeridas por el proyecto TechClassUC.

Gráficas producidas
-------------------
1. Evolución temporal del número de clientes en el sistema.
2. Histograma de tiempos de espera Wq.
3. Curva Wq promedio vs número de servidores c.
4. Curva ρ vs λ para distintos valores de c.
5. Distribución de las medias de Wq entre réplicas (normalidad TCL).
6. Heatmap de Wq para análisis de sensibilidad.
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")          # sin GUI — funciona en servidores/contenedores
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SALIDA_DIR = "graficas"
os.makedirs(SALIDA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _guardar(nombre: str, fig) -> str:
    ruta = os.path.join(SALIDA_DIR, nombre)
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return ruta


# ---------------------------------------------------------------------------
# 1. Evolución temporal del número de clientes
# ---------------------------------------------------------------------------

def grafica_evolucion_temporal(lam: float, mu: float, c: int,
                               t_sim: float = 480.0, semilla: int = 42) -> str:
    """
    Simula una réplica y registra el número de clientes en el sistema en cada evento.
    """
    import random, simpy

    random.seed(semilla)
    tiempos, n_sistema = [], []
    lam_min = lam / 60.0
    mu_min = mu / 60.0

    env = simpy.Environment()
    recurso = simpy.Resource(env, capacity=c)
    en_sistema = [0]

    def cliente_proc(arrival_time):
        en_sistema[0] += 1
        tiempos.append(env.now)
        n_sistema.append(en_sistema[0])
        with recurso.request() as req:
            yield req
            t_srv = random.expovariate(mu_min)
            yield env.timeout(t_srv)
        en_sistema[0] -= 1
        tiempos.append(env.now)
        n_sistema.append(en_sistema[0])

    def generador():
        while True:
            yield env.timeout(random.expovariate(lam_min))
            if env.now > t_sim:
                break
            env.process(cliente_proc(env.now))

    env.process(generador())
    env.run(until=t_sim)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.step(tiempos, n_sistema, where="post", color="#2563eb", linewidth=0.8)
    ax.axhline(c, color="#dc2626", linestyle="--", linewidth=1,
               label=f"Capacidad c = {c}")
    ax.set_xlabel("Tiempo (minutos)")
    ax.set_ylabel("Clientes en sistema")
    ax.set_title("Evolución temporal del número de clientes en el sistema")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return _guardar("1_evolucion_temporal.png", fig)


# ---------------------------------------------------------------------------
# 2. Histograma de tiempos de espera Wq
# ---------------------------------------------------------------------------

def grafica_histograma_wq(wq_todas: list, lam: float, mu: float, c: int) -> str:
    """Histograma de todos los Wq individuales registrados."""
    from analitico import calcular_mmc

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(wq_todas, bins=40, color="#3b82f6", edgecolor="white",
            alpha=0.85, density=True, label="Simulado")

    teo = calcular_mmc(lam, mu, c)
    if teo:
        ax.axvline(teo["Wq"], color="#dc2626", linewidth=2,
                   linestyle="--", label=f"Wq teórico = {teo['Wq']:.2f} min")

    media_sim = np.mean(wq_todas)
    ax.axvline(media_sim, color="#16a34a", linewidth=2,
               linestyle="-.", label=f"Wq simulado = {media_sim:.2f} min")

    ax.set_xlabel("Tiempo de espera en cola Wq (minutos)")
    ax.set_ylabel("Densidad")
    ax.set_title("Distribución de tiempos de espera en cola (Wq)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return _guardar("2_histograma_wq.png", fig)


# ---------------------------------------------------------------------------
# 3. Curva Wq promedio vs número de servidores c
# ---------------------------------------------------------------------------

def grafica_wq_vs_c(lam: float, mu: float, c_rango: list,
                    N: int = 30, t_sim: float = 480.0,
                    t_warm: float = 60.0) -> str:
    """Wq simulado y analítico en función de c."""
    from montecarlo import correr_replicas
    from analitico import calcular_mmc

    wq_sim, wq_teo = [], []

    for c in c_rango:
        rho = lam / (c * mu)
        if rho >= 1.0:
            wq_sim.append(np.nan)
            wq_teo.append(np.nan)
            continue

        res = correr_replicas(N=N, lam=lam, mu=mu, c=c,
                              t_sim=t_sim, t_warm=t_warm)
        wq_sim.append(res["resumen"]["wq_promedio"]["media"])

        teo = calcular_mmc(lam, mu, c)
        wq_teo.append(teo["Wq"] if teo else np.nan)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(c_rango, wq_sim, "o-", color="#2563eb", label="Simulación")
    ax.plot(c_rango, wq_teo, "s--", color="#dc2626", label="Analítico M/M/c")
    ax.axhline(10, color="#16a34a", linestyle=":", linewidth=1.5,
               label="Umbral objetivo (10 min)")
    ax.set_xlabel("Número de técnicos (c)")
    ax.set_ylabel("Wq promedio (minutos)")
    ax.set_title(f"Tiempo de espera en cola vs Número de técnicos (λ={lam})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    return _guardar("3_wq_vs_c.png", fig)


# ---------------------------------------------------------------------------
# 4. Curva ρ vs λ para distintos valores de c
# ---------------------------------------------------------------------------

def grafica_rho_vs_lam(mu: float, c_lista: list,
                       lam_rango: np.ndarray | None = None) -> str:
    """Factor de utilización ρ en función de λ para varios valores de c."""
    if lam_rango is None:
        lam_rango = np.linspace(1, 20, 200)

    fig, ax = plt.subplots(figsize=(9, 4))
    colores = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed"]

    for idx, c in enumerate(c_lista):
        rho_vals = lam_rango / (c * mu)
        color = colores[idx % len(colores)]
        ax.plot(lam_rango, rho_vals, label=f"c = {c}", color=color)

    ax.axhline(1.0, color="black", linestyle="--", linewidth=1,
               label="Límite estabilidad (ρ=1)")
    ax.set_xlabel("Tasa de llegada λ (clientes/hora)")
    ax.set_ylabel("Factor de utilización ρ")
    ax.set_title("Factor de utilización ρ vs Tasa de llegada λ")
    ax.set_ylim(0, 1.5)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return _guardar("4_rho_vs_lambda.png", fig)


# ---------------------------------------------------------------------------
# 5. Distribución de medias Wq entre réplicas (TCL)
# ---------------------------------------------------------------------------

def grafica_distribucion_medias_wq(replicas: list, lam: float,
                                   mu: float, c: int) -> str:
    """
    Histograma de las medias Wq de cada réplica para verificar normalidad
    por el Teorema Central del Límite.
    """
    from analitico import calcular_mmc

    medias_wq = [r["wq_promedio"] for r in replicas]
    media_global = np.mean(medias_wq)
    std_global = np.std(medias_wq, ddof=1)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(medias_wq, bins=10, color="#3b82f6", edgecolor="white",
            alpha=0.8, density=True, label="Medias de réplicas")

    # Curva normal ajustada — usando NumPy puro (sin scipy)
    x = np.linspace(min(medias_wq) - std_global,
                    max(medias_wq) + std_global, 200)
    normal_y = (1.0 / (std_global * np.sqrt(2 * np.pi))) * np.exp(
        -0.5 * ((x - media_global) / std_global) ** 2
    )
    ax.plot(x, normal_y, "r-", linewidth=2, label="Normal ajustada")

    teo = calcular_mmc(lam, mu, c)
    if teo:
        ax.axvline(teo["Wq"], color="#16a34a", linestyle="--", linewidth=2,
                   label=f"Wq analítico = {teo['Wq']:.2f} min")

    ax.set_xlabel("Media de Wq por réplica (minutos)")
    ax.set_ylabel("Densidad")
    ax.set_title("Distribución de medias de Wq — Verificación TCL")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return _guardar("5_distribucion_medias_wq.png", fig)


# ---------------------------------------------------------------------------
# 6. Heatmap de Wq — análisis de sensibilidad
# ---------------------------------------------------------------------------

def grafica_heatmap_sensibilidad(sens: dict) -> str:
    """
    Heatmap de Wq promedio para cada combinación (c, λ) del análisis
    de sensibilidad.
    """
    wq_matrix  = sens["wq_matrix"]
    c_vals     = sens["c_valores"]
    lam_vals   = sens["lam_valores"]

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(wq_matrix, aspect="auto", cmap="YlOrRd",
                   origin="lower",
                   extent=[lam_vals[0] - 0.5, lam_vals[-1] + 0.5,
                           c_vals[0]   - 0.5, c_vals[-1]   + 0.5])
    plt.colorbar(im, ax=ax, label="Wq promedio (minutos)")

    # Anotaciones en cada celda
    for i, c in enumerate(c_vals):
        for j, lam in enumerate(lam_vals):
            val = wq_matrix[i, j]
            texto = "N/A" if np.isnan(val) else f"{val:.1f}"
            ax.text(lam, c, texto, ha="center", va="center",
                    fontsize=8, color="black")

    ax.set_xlabel("Tasa de llegada λ (clientes/hora)")
    ax.set_ylabel("Número de técnicos c")
    ax.set_title("Heatmap de Wq promedio — Análisis de Sensibilidad")
    ax.set_xticks(lam_vals)
    ax.set_yticks(c_vals)
    return _guardar("6_heatmap_sensibilidad.png", fig)