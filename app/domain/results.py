"""
Modelos de dominio: KpiSnapshot, RunResult, ComparisonResult.
"""
from pydantic import BaseModel, Field


class StandKpi(BaseModel):
    """KPIs por puesto en un instante o fase."""

    stand_id: str
    queue_length: int = 0
    avg_wait_min: float = 0.0
    max_wait_min: float = 0.0
    abandonment_rate: float = 0.0
    occupancy: float = 0.0
    density: float = 0.0
    registers_open: int = 0
    staff: int = 0
    estimated_wait_min: float = 0.0
    revenue: float = 0.0


class KpiSnapshot(BaseModel):
    """Fotografía del estado de la simulación en un minuto."""

    minute: int
    phase: str
    stands: list[StandKpi] = Field(default_factory=list)
    global_avg_wait_min: float = 0.0
    global_max_queue: int = 0
    global_abandonment_rate: float = 0.0
    global_occupancy: float = 0.0
    global_revenue: float = 0.0


class PhaseResult(BaseModel):
    """Resultados agregados de una fase."""

    phase: str
    avg_wait_min: float = 0.0
    max_wait_min: float = 0.0
    max_queue: int = 0
    abandonment_rate: float = 0.0
    occupancy: float = 0.0
    max_density: float = 0.0
    revenue: float = 0.0
    total_served: int = 0
    total_abandoned: int = 0


class RunResult(BaseModel):
    """Resultado final de una corrida."""

    run_id: str
    scenario_id: str
    mode: str
    seed: int
    total_minutes: int = 0
    phases: list[PhaseResult] = Field(default_factory=list)
    global_avg_wait_min: float = 0.0
    global_abandonment_rate: float = 0.0
    global_occupancy: float = 0.0
    global_revenue: float = 0.0
    total_served: int = 0
    total_abandoned: int = 0


class ReplicaResult(BaseModel):
    """Resultados de una réplica (base + agente)."""

    seed: int
    base: RunResult
    agent: RunResult


class PhaseAggregates(BaseModel):
    """Estadísticas agregadas de una fase en la comparación."""

    phase: str
    avg_wait_mean: float = 0.0
    avg_wait_std: float = 0.0
    abandonment_mean: float = 0.0
    abandonment_std: float = 0.0
    occupancy_mean: float = 0.0
    occupancy_std: float = 0.0
    max_density_mean: float = 0.0
    halftime_wait_reduction_pct: float | None = None


class ComparisonResult(BaseModel):
    """Resultado de la comparación entre base y agente con N réplicas."""

    id: str
    scenario_id: str
    replicas: int
    seeds: list[int]
    phase_aggregates: list[PhaseAggregates] = Field(default_factory=list)
    global_avg_wait_reduction_pct: float = 0.0
    global_abandonment_reduction_pct: float = 0.0
    replica_results: list[ReplicaResult] = Field(default_factory=list)
