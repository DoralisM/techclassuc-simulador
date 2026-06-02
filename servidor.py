"""
servidor.py
-----------
Configura el recurso SimPy que modela los técnicos (servidores) del sistema
y mantiene estadísticas de uso por instancia.
"""

import simpy
from dataclasses import dataclass, field


@dataclass
class EstadisticasServidor:
    """Acumula métricas de rendimiento para un recurso SimPy compartido."""
    clientes_atendidos: int = 0
    tiempo_ocupado: float = 0.0        # minutos acumulados en atención
    tiempo_total_sim: float = 0.0      # duración total de la simulación

    def registrar_servicio(self, duracion: float) -> None:
        """Registra la finalización de un servicio."""
        self.clientes_atendidos += 1
        self.tiempo_ocupado += duracion

    def utilizacion_promedio(self, c: int) -> float:
        """
        Fracción promedio de tiempo que los c servidores estuvieron ocupados.
        ρ = tiempo_ocupado / (c * tiempo_total_sim)
        """
        denominador = c * self.tiempo_total_sim
        if denominador <= 0:
            return 0.0
        return self.tiempo_ocupado / denominador


def crear_recurso(env: simpy.Environment, capacidad: int) -> simpy.Resource:
    """
    Crea y retorna un simpy.Resource con la capacidad dada (número de técnicos).

    Parameters
    ----------
    env : simpy.Environment
        Entorno de simulación activo.
    capacidad : int
        Número de servidores (técnicos) disponibles en paralelo.

    Returns
    -------
    simpy.Resource
        Recurso listo para ser solicitado por los procesos cliente.
    """
    return simpy.Resource(env, capacity=capacidad)


def crear_recurso_prioridad(env: simpy.Environment, capacidad: int) -> simpy.PriorityResource:
    """
    Crea un simpy.PriorityResource para manejo de clientes urgentes.

    Parameters
    ----------
    env : simpy.Environment
    capacidad : int

    Returns
    -------
    simpy.PriorityResource
    """
    return simpy.PriorityResource(env, capacity=capacidad)
