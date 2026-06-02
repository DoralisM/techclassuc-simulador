"""
main.py
-------
Punto de entrada del simulador TechClassUC.
Orquesta la ejecución de todos los módulos y genera el reporte final.

Uso
---
    python main.py                          # parámetros base
    python main.py --lam 12 --c 4           # personalizado
    python main.py --help                   # ayuda
"""

import argparse
import sys

from analitico import calcular_mmc, comparar_con_simulacion, imprimir_resultados_analiticos
from montecarlo import correr_replicas
from sensibilidad import analisis_sensibilidad, imprimir_tabla_sensibilidad
from visualizacion import (
    grafica_evolucion_temporal,
    grafica_histograma_wq,
    grafica_wq_vs_c,
    grafica_rho_vs_lam,
    grafica_distribucion_medias_wq,
    grafica_heatmap_sensibilidad,
)


# ---------------------------------------------------------------------------
# Argumentos CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Simulador TechClassUC — M/M/c con SimPy")
    p.add_argument("--lam",        type=float, default=10.0,  help="Tasa de llegada λ (cl/h)")
    p.add_argument("--mu",         type=float, default=4.0,   help="Tasa de servicio μ (cl/h por técnico)")
    p.add_argument("--c",          type=int,   default=3,     help="Número de técnicos")
    p.add_argument("--t_sim",      type=float, default=480.0, help="Duración simulación (min)")
    p.add_argument("--t_warm",     type=float, default=60.0,  help="Período de calentamiento (min)")
    p.add_argument("--N",          type=int,   default=30,    help="Número de réplicas Montecarlo")
    p.add_argument("--semilla",    type=int,   default=42,    help="Semilla base")
    p.add_argument("--prioridad",  action="store_true",       help="Habilitar cola con prioridad")
    p.add_argument("--sin_graficas", action="store_true",     help="Omitir generación de gráficas")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Helpers de reporte
# ---------------------------------------------------------------------------

def _separador(titulo: str = "", ancho: int = 60) -> None:
    if titulo:
        lado = (ancho - len(titulo) - 2) // 2
        print("=" * lado + f" {titulo} " + "=" * lado)
    else:
        print("=" * ancho)


def _imprimir_resumen_mc(resumen: dict, n_min: int) -> None:
    _separador("RESULTADOS MONTECARLO")
    fmt = "  {:<22} {:>10.4f}   IC95% [{:.4f}, {:.4f}]"
    for k, v in resumen.items():
        if k == "n_clientes":
            print(f"  {'Clientes atendidos':<22} {v['media']:>10.1f}")
        else:
            print(fmt.format(k, v["media"], v["ic_inferior"], v["ic_superior"]))
    print(f"\n  Réplicas mínimas (error ≤ 5%): {n_min}")
    _separador()


def _imprimir_comparacion(tabla: list) -> None:
    _separador("VALIDACIÓN ANALÍTICA vs SIMULACIÓN")
    print(f"  {'Métrica':<8} {'Teórico':>12} {'Simulado':>12} {'Error %':>10}")
    print("  " + "-" * 46)
    for fila in tabla:
        print(f"  {fila['metrica']:<8} {fila['valor_teorico']:>12.4f} "
              f"{fila['valor_simulado']:>12.4f} {fila['error_relativo_pct']:>9.2f}%")
    _separador()


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    lam, mu, c = args.lam, args.mu, args.c

    # ------------------------------------------------------------------ #
    # 0. Validar estabilidad
    # ------------------------------------------------------------------ #
    rho = lam / (c * mu)
    print(f"\n{'='*60}")
    print(f"  TechClassUC — Simulador de Colas M/M/c")
    print(f"{'='*60}")
    print(f"  λ={lam} cl/h  μ={mu} cl/h  c={c}  ρ={rho:.4f}")

    if rho >= 1.0:
        print(f"\n⛔  SISTEMA INESTABLE (ρ = {rho:.4f} ≥ 1).")
        print("    Aumenta c o reduce λ antes de simular.")
        sys.exit(1)

    print(f"  ✅ Sistema estable. Iniciando simulación…\n")

    # ------------------------------------------------------------------ #
    # 1. Resultados analíticos M/M/c
    # ------------------------------------------------------------------ #
    imprimir_resultados_analiticos(lam, mu, c)

    # ------------------------------------------------------------------ #
    # 2. Simulación de Montecarlo
    # ------------------------------------------------------------------ #
    print(f"\n  Ejecutando {args.N} réplicas DES…")
    mc = correr_replicas(
        N=args.N, lam=lam, mu=mu, c=c,
        t_sim=args.t_sim, t_warm=args.t_warm,
        semilla_base=args.semilla,
        usar_prioridad=args.prioridad,
    )
    _imprimir_resumen_mc(mc["resumen"], mc["n_minimo"])

    # ------------------------------------------------------------------ #
    # 3. Validación analítica
    # ------------------------------------------------------------------ #
    tabla_comp = comparar_con_simulacion(lam, mu, c, mc["resumen"])
    _imprimir_comparacion(tabla_comp)

    # ------------------------------------------------------------------ #
    # 4. Análisis de sensibilidad
    # ------------------------------------------------------------------ #
    print("\n  Ejecutando análisis de sensibilidad…")
    sens = analisis_sensibilidad(
        mu=mu, t_sim=args.t_sim, t_warm=args.t_warm,
        N=min(args.N, 15),    # réplicas reducidas para el barrido
        semilla_base=args.semilla,
    )
    imprimir_tabla_sensibilidad(sens)

    # ------------------------------------------------------------------ #
    # 5. Gráficas
    # ------------------------------------------------------------------ #
    if not args.sin_graficas:
        import numpy as np
        print("\n  Generando gráficas…")

        g1 = grafica_evolucion_temporal(lam, mu, c, args.t_sim, args.semilla)
        print(f"  ✔ {g1}")

        g2 = grafica_histograma_wq(mc["wq_todas"], lam, mu, c)
        print(f"  ✔ {g2}")

        g3 = grafica_wq_vs_c(
            lam=lam, mu=mu,
            c_rango=list(range(max(1, c - 2), c + 5)),
            N=min(args.N, 15),
            t_sim=args.t_sim, t_warm=args.t_warm,
        )
        print(f"  ✔ {g3}")

        g4 = grafica_rho_vs_lam(
            mu=mu,
            c_lista=list(range(max(1, c - 2), c + 4)),
        )
        print(f"  ✔ {g4}")

        g5 = grafica_distribucion_medias_wq(mc["replicas"], lam, mu, c)
        print(f"  ✔ {g5}")

        g6 = grafica_heatmap_sensibilidad(sens)
        print(f"  ✔ {g6}")

    # ------------------------------------------------------------------ #
    # 6. Recomendación final
    # ------------------------------------------------------------------ #
    _separador("RECOMENDACIÓN")
    wq_sim = mc["resumen"]["wq_promedio"]["media"]
    print(f"  Wq simulado = {wq_sim:.2f} min  (umbral objetivo: 10 min)")
    if wq_sim <= 10.0:
        print(f"  ✅ Con c = {c} técnicos el sistema cumple el objetivo.")
    else:
        # Buscar c mínimo que cumpla
        for c_opt in range(c + 1, c + 10):
            if lam / (c_opt * mu) >= 1.0:
                continue
            res_opt = correr_replicas(
                N=15, lam=lam, mu=mu, c=c_opt,
                t_sim=args.t_sim, t_warm=args.t_warm,
                semilla_base=args.semilla,
            )
            if res_opt["resumen"]["wq_promedio"]["media"] <= 10.0:
                print(f"  ⚠️  Se recomienda c = {c_opt} técnicos para Wq ≤ 10 min.")
                break
    _separador()


if __name__ == "__main__":
    main()
