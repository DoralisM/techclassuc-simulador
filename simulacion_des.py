"""
simulacion_des.py
-----------------
Implementa el modelo de simulación de eventos discretos (DES) con SimPy
para el sistema de atención al cliente de TechClassUC.

Contiene:
  - proceso_cliente()   : flujo individual de un cliente en el sistema.
  - generador_llegadas(): proceso que inyecta clientes al sistema.
  - correr_una_replica(): ejecuta una réplica completa de la simulación.
"""

import random
import simpy
from typing import Optional

from cliente import Cliente
from servidor import crear_recurso, crear_recurso_prioridad, EstadisticasServidor


# ---------------------------------------------------------------------------
# Proceso: ciclo de vida de un cliente
# ---------------------------------------------------------------------------

def proceso_cliente(
    env: simpy.Environment,
    cliente: Cliente,
    recurso,
    mu: float,
    stats: EstadisticasServidor,
    clientes_terminados: list,
    t_warm: float,
    usar_prioridad: bool = False,
) -> None:
    """
    Proceso SimPy que modela el ciclo de vida de un cliente:
    llega → solicita servidor → espera → es atendido → libera servidor.

    Parameters
    ----------
    env             : entorno SimPy activo.
    cliente         : objeto Cliente con sus atributos.
    recurso         : simpy.Resource o PriorityResource.
    mu              : tasa de servicio (clientes/hora por técnico).
    stats           : objeto para acumular estadísticas de servidor.
    clientes_terminados : lista donde se depositan clientes completados.
    t_warm          : duración del período de calentamiento en minutos.
    usar_prioridad  : si True, se usa request con prioridad.
    """
    mu_min = mu / 60.0          # convertir a clientes/minuto

    # Solicitar servidor
    if usar_prioridad:
        req = recurso.request(priority=cliente.prioridad)
    else:
        req = recurso.request()

    yield req                   # esperar hasta obtener servidor

    cliente.t_inicio = env.now

    # Tiempo de servicio ~ Exponencial(mu_min)
    t_servicio = random.expovariate(mu_min)
    yield env.timeout(t_servicio)

    cliente.t_fin = env.now
    recurso.release(req)

    if cliente.t_fin >= t_warm:
      stats.registrar_servicio(t_servicio)
      clientes_terminados.append(cliente)


# ---------------------------------------------------------------------------
# Proceso: generador de llegadas
# ---------------------------------------------------------------------------

def generador_llegadas(
    env: simpy.Environment,
    lam: float,
    mu: float,
    c: int,
    t_sim: float,
    t_warm: float,
    stats: EstadisticasServidor,
    clientes_terminados: list,
    usar_prioridad: bool = False,
    proporcion_urgentes: float = 0.15,
) -> None:
    """
    Genera clientes con inter-llegadas ~ Exponencial(λ) durante [0, t_sim].

    Parameters
    ----------
    lam                 : tasa de llegada (clientes/hora).
    mu                  : tasa de servicio (clientes/hora por técnico).
    c                   : número de técnicos.
    t_sim               : duración total de la simulación (minutos).
    t_warm              : período de calentamiento (minutos).
    stats               : estadísticas del servidor compartido.
    clientes_terminados : lista de resultados.
    usar_prioridad      : habilita cola con prioridad.
    proporcion_urgentes : fracción de clientes con prioridad urgente.
    """
    lam_min = lam / 60.0        # convertir a clientes/minuto
    tipos = Cliente.TIPOS

    if usar_prioridad:
        recurso = crear_recurso_prioridad(env, c)
    else:
        recurso = crear_recurso(env, c)

    cliente_id = 0
    while True:
        # Tiempo hasta la próxima llegada
        t_entre_llegadas = random.expovariate(lam_min)
        yield env.timeout(t_entre_llegadas)

        if env.now >= t_sim:
         break 

        cliente_id += 1
        tipo = random.choice(tipos)
        prioridad = 0 if random.random() < proporcion_urgentes else 1

        cliente = Cliente(
            cliente_id=cliente_id,
            tipo=tipo,
            prioridad=prioridad,
            t_llegada=env.now,
        )

        env.process(
            proceso_cliente(
                env, cliente, recurso, mu,
                stats, clientes_terminados, t_warm, usar_prioridad
            )
        )


# ---------------------------------------------------------------------------
# Función principal: una réplica completa
# ---------------------------------------------------------------------------

def correr_una_replica(
    lam: float,
    mu: float,
    c: int,
    t_sim: float = 480.0,
    t_warm: float = 60.0,
    semilla: Optional[int] = None,
    usar_prioridad: bool = False,
) -> dict:
    """
    Ejecuta una réplica de la simulación DES y retorna las métricas.

    Parameters
    ----------
    lam     : tasa de llegada (clientes/hora).
    mu      : tasa de servicio (clientes/hora por técnico).
    c       : número de técnicos.
    t_sim   : duración de la simulación (minutos).
    t_warm  : período de calentamiento a descartar (minutos).
    semilla : semilla aleatoria para reproducibilidad.
    usar_prioridad : habilitar simpy.PriorityResource.

    Returns
    -------
    dict con claves:
        wq_promedio, ws_promedio, lq_promedio, rho,
        n_clientes, wq_lista, ws_lista
    """
    if semilla is not None:
        random.seed(semilla)

    env = simpy.Environment()
    stats = EstadisticasServidor()
    clientes_terminados: list[Cliente] = []

    env.process(
        generador_llegadas(
            env, lam, mu, c, t_sim, t_warm,
            stats, clientes_terminados, usar_prioridad
        )
    )
# Correr hasta el t_sim + drain para que los clientes terminen
    t_drain = t_sim +10.0 *(60.0 / mu)
    env.run(until=t_drain)

    stats.tiempo_total_sim = t_sim - t_warm  # periodo estacionario

    # Calcular métricas solo con clientes del período estacionario
    wq_lista = [cl.calcular_wq() for cl in clientes_terminados]
    ws_lista = [cl.calcular_ws() for cl in clientes_terminados]
    n = len(wq_lista)

    wq_prom = sum(wq_lista) / n if n > 0 else 0.0
    ws_prom = sum(ws_lista) / n if n > 0 else 0.0

    # Lq estimado por Ley de Little: Lq = λ * Wq  (en clientes, λ en /min)
    lam_min = lam / 60.0
    lq_prom = lam_min * wq_prom

    rho = stats.utilizacion_promedio(c)

    return {
        "wq_promedio": wq_prom,
        "ws_promedio": ws_prom,
        "lq_promedio": lq_prom,
        "rho": rho,
        "n_clientes": n,
        "wq_lista": wq_lista,
        "ws_lista": ws_lista,
    }
    