"""
cliente.py
----------
Define la clase Cliente con todos sus atributos y métodos para calcular
las métricas de tiempo de espera (Wq) y tiempo en sistema (Ws).
"""


class Cliente:
    """
    Representa una solicitud de servicio que llega al sistema de TechClassUC.

    Atributos
    ---------
    cliente_id : int
        Identificador único del cliente.
    tipo : str
        Tipo de solicitud: 'soporte', 'mantenimiento' o 'reclamo'.
    prioridad : int
        Prioridad en cola: 0 = urgente, 1 = normal (menor valor = mayor prioridad).
    t_llegada : float
        Tiempo de llegada al sistema (minutos desde inicio de simulación).
    t_inicio : float | None
        Tiempo en que empieza a ser atendido.
    t_fin : float | None
        Tiempo en que termina la atención.
    """

    TIPOS = ("soporte", "mantenimiento", "reclamo")

    def __init__(self, cliente_id: int, tipo: str = "soporte",
                 prioridad: int = 1, t_llegada: float = 0.0):
        self.cliente_id = cliente_id
        self.tipo = tipo
        self.prioridad = prioridad          # 0=urgente, 1=normal
        self.t_llegada: float = t_llegada
        self.t_inicio: float | None = None
        self.t_fin: float | None = None

    # ------------------------------------------------------------------
    # Métricas derivadas
    # ------------------------------------------------------------------

    def calcular_wq(self) -> float:
        """
        Tiempo de espera en cola (Wq = t_inicio - t_llegada).

        Returns
        -------
        float
            Wq en minutos. Devuelve 0.0 si el cliente aún no ha sido atendido.
        """
        if self.t_inicio is None:
            return 0.0
        return self.t_inicio - self.t_llegada

    def calcular_ws(self) -> float:
        """
        Tiempo total en el sistema (Ws = t_fin - t_llegada).

        Returns
        -------
        float
            Ws en minutos. Devuelve 0.0 si el cliente aún no ha salido.
        """
        if self.t_fin is None:
            return 0.0
        return self.t_fin - self.t_llegada

    def calcular_tiempo_servicio(self) -> float:
        """
        Tiempo efectivo de atención (t_fin - t_inicio).

        Returns
        -------
        float
            Duración del servicio en minutos.
        """
        if self.t_inicio is None or self.t_fin is None:
            return 0.0
        return self.t_fin - self.t_inicio

    def __repr__(self) -> str:
        return (
            f"Cliente(id={self.cliente_id}, tipo={self.tipo}, "
            f"prioridad={'urgente' if self.prioridad == 0 else 'normal'}, "
            f"t_llegada={self.t_llegada:.2f})"
        )
