"""
Estado mutable de la simulación.
Una instancia de SimState se crea por corrida y se puede clonar de forma
independiente para la búsqueda anticipada del agente.
"""
import copy
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StandState:
    """Estado en tiempo de ejecución de un puesto."""

    stand_id: str
    registers_open: int
    staff: int
    pickup_enabled: bool
    # Cola: lista de (tiempo_llegada, perfil, tiempo_servicio_s)
    queue: list[tuple[float, str, float]] = field(default_factory=list)
    # Fracción de servicio acumulada (evita perder capacidad parcial)
    service_accumulator: float = 0.0
    # Pickup accumulator (para pedido_movil)
    pickup_accumulator: float = 0.0

    # Métricas acumuladas (reiniciadas entre fases cuando se consultan)
    total_served: int = 0
    total_abandoned: int = 0
    total_wait_min: float = 0.0
    max_wait_min: float = 0.0
    total_service_time_min: float = 0.0  # tiempo que las cajas estuvieron ocupadas
    transit_count: int = 0  # personas en tránsito hacia este puesto

    # Redirección activa: sector_id -> puesto_destino (o None para desactivar)
    redirections: dict[str, str] = field(default_factory=dict)


@dataclass
class SimState:
    """Estado completo de la simulación en un instante."""

    scenario_id: str
    seed: int
    current_minute: int = 0
    phase_index: int = 0
    phase_minute: int = 0  # minuto dentro de la fase actual
    finished: bool = False

    # Diccionario stand_id -> StandState
    stands: dict[str, StandState] = field(default_factory=dict)

    # RNG con estado copiable — clave para la reproducibilidad del agente
    rng: random.Random = field(default_factory=lambda: random.Random())

    # Historial de snapshots de métricas por minuto (para línea de tiempo)
    history: list[dict[str, Any]] = field(default_factory=list)

    # Parámetros del escenario necesarios en el motor
    # (se copian del Scenario para que el motor no dependa del dominio en caliente)
    attendance: int = 0
    redirect_compliance: float = 0.60
    anticipation_share: float = 0.0


def build_state(scenario: Any, seed: int | None = None) -> "SimState":
    """Construye un SimState inicial a partir de un Scenario."""
    from app.domain.scenario import Scenario  # import local para no crear ciclo

    sc: Scenario = scenario
    effective_seed = seed if seed is not None else sc.seed
    rng = random.Random(effective_seed)

    stands: dict[str, StandState] = {}
    for st in sc.stands:
        stands[st.id] = StandState(
            stand_id=st.id,
            registers_open=st.registers_open,
            staff=st.staff,
            pickup_enabled=st.pickup_enabled,
        )

    state = SimState(
        scenario_id=sc.id,
        seed=effective_seed,
        stands=stands,
        attendance=sc.attendance,
        redirect_compliance=sc.redirect_compliance,
        anticipation_share=sc.anticipation_share,
    )
    state.rng = rng
    return state


def clone_state(state: SimState) -> SimState:
    """
    Clona el estado profundamente para que la búsqueda anticipada del agente
    no altere la corrida real.
    El estado del RNG se copia con deepcopy, garantizando misma trayectoria.
    """
    return copy.deepcopy(state)
