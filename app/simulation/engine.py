"""
Motor de simulación.
SimulationEngine encapsula el ciclo de avance por pasos de 1 minuto.
No importa nada de api/, services/ ni agent/.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.simulation.state import SimState, clone_state
from app.simulation.demand import generate_arrivals
from app.simulation.routing import choose_stand, walk_time
from app.simulation import kpis as kpi_module
from app.simulation.kpis import PICKUP_SERVICE_SECONDS

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.domain.results import KpiSnapshot


class SimulationEngine:
    """
    Gestiona el avance de la simulación paso a paso.
    Recibe un Scenario inmutable y opera sobre un SimState mutable.
    """

    def __init__(self, scenario: "Scenario", state: SimState) -> None:
        self.scenario = scenario
        self.state = state

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def step(self, minutes: int = 1) -> "KpiSnapshot":
        """Avanza la simulación `minutes` pasos de 1 minuto cada uno."""
        if self.state.finished:
            return kpi_module.snapshot(self.state, self.scenario)
        snap: "KpiSnapshot" | None = None
        for _ in range(minutes):
            if self.state.finished:
                break
            snap = self._step_one()
        return snap or kpi_module.snapshot(self.state, self.scenario)

    def snapshot(self) -> "KpiSnapshot":
        """Devuelve el estado actual sin avanzar."""
        return kpi_module.snapshot(self.state, self.scenario)

    def clone(self) -> "SimulationEngine":
        """
        Clona el motor (incluye estado profundo con el RNG).
        La copia es completamente independiente; avanzarla no altera el original.
        """
        return SimulationEngine(self.scenario, clone_state(self.state))

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _step_one(self) -> "KpiSnapshot":
        state = self.state
        scenario = self.scenario

        # 1. Determinar fase y minuto
        self._update_phase()
        if state.finished:
            return kpi_module.snapshot(state, scenario)

        # 2. Generar llegadas
        arrivals = generate_arrivals(state, scenario)

        # 3 y 4. Elegir puesto y decidir abandono
        from app.config import get_settings
        settings = get_settings()
        tau = settings.routing_tau
        walk_mpu = settings.walk_min_per_unit

        for sector_id, profile_name in arrivals:
            stand_id = choose_stand(sector_id, profile_name, state, scenario, tau, walk_mpu)
            stand_state = state.stands[stand_id]
            stand_cfg = next(s for s in scenario.stands if s.id == stand_id)
            profile_cfg = next(p for p in scenario.profiles if p.name == profile_name)
            sector_cfg = next(s for s in scenario.sectors if s.id == sector_id)

            # Tiempo de caminata
            walk = walk_time(sector_cfg, stand_cfg, walk_mpu)
            est_wait = kpi_module.estimated_wait_min(stand_state, scenario)

            # 4. Abandono al llegar si espera_estimada + caminata > paciencia
            if est_wait + walk > profile_cfg.patience_min:
                stand_state.total_abandoned += 1
                continue

            # Tiempo de servicio (pickup si corresponde)
            if profile_name == "pedido_movil" and stand_state.pickup_enabled:
                service_s = PICKUP_SERVICE_SECONDS
            else:
                service_s = profile_cfg.service_seconds

            # 5. Encolar
            stand_state.queue.append((float(state.current_minute) + walk, profile_name, service_s))
            stand_state.transit_count = max(0, stand_state.transit_count - 1)

        # 6. Atender
        self._serve_all()

        # 7. Actualizar métricas de snapshot
        snap = kpi_module.snapshot(state, scenario)
        state.history.append({
            "minute": state.current_minute,
            "phase": scenario.phases[state.phase_index].name,
            "global_avg_wait_min": snap.global_avg_wait_min,
            "global_max_queue": snap.global_max_queue,
            "global_abandonment_rate": snap.global_abandonment_rate,
            "global_occupancy": snap.global_occupancy,
        })

        # 8. Avanzar reloj
        state.current_minute += 1
        state.phase_minute += 1

        return snap

    def _update_phase(self) -> None:
        """Avanza el índice de fase si se agotaron los minutos de la fase actual."""
        state = self.state
        scenario = self.scenario
        phases = scenario.phases

        if state.phase_index >= len(phases):
            state.finished = True
            return

        current_phase = phases[state.phase_index]
        if state.phase_minute >= current_phase.duration_min:
            # Pasar a la siguiente fase
            state.phase_index += 1
            state.phase_minute = 0
            # Reiniciar acumuladores de métricas al cambiar de fase
            if state.phase_index >= len(phases):
                state.finished = True
            else:
                self._reset_phase_metrics()

    def _reset_phase_metrics(self) -> None:
        """Reinicia los contadores acumulados de todos los puestos (nueva fase)."""
        for ss in self.state.stands.values():
            ss.total_served = 0
            ss.total_abandoned = 0
            ss.total_wait_min = 0.0
            ss.max_wait_min = 0.0
            ss.total_service_time_min = 0.0

    def _serve_all(self) -> None:
        """Procesa las atenciones de este minuto en todos los puestos."""
        minute = float(self.state.current_minute)
        for stand_id, ss in self.state.stands.items():
            self._serve_stand(ss, minute)

    def _serve_stand(self, ss, minute: float) -> None:
        """
        Atiende a las personas en la cola del puesto durante 1 minuto.
        Usa un acumulador de capacidad: cada minuto se suman registers_open × rate_per_register
        atenciones disponibles; se consume 1 por cada persona atendida.
        La fracción sobrante se lleva al siguiente minuto para no perder capacidad.
        """
        if ss.registers_open == 0 or not ss.queue:
            return

        # Añadir capacidad del minuto actual al acumulador
        rate_per_register = self._stand_rate(ss)
        ss.service_accumulator += ss.registers_open * rate_per_register

        while ss.queue and ss.service_accumulator >= 1.0:
            arrival_min, profile_name, service_s = ss.queue[0]
            if minute < arrival_min:
                # Persona aún en tránsito; no se puede atender todavía
                break

            effective_s = service_s
            if profile_name == "pedido_movil" and ss.pickup_enabled:
                effective_s = PICKUP_SERVICE_SECONDS

            wait = max(minute - arrival_min, 0.0)
            ss.total_wait_min += wait
            ss.max_wait_min = max(ss.max_wait_min, wait)
            ss.total_served += 1
            ss.total_service_time_min += effective_s / 60.0
            ss.queue.pop(0)
            ss.service_accumulator -= 1.0

        # Sin cola: limpiar el acumulador para evitar crédito infinito
        if not ss.queue:
            ss.service_accumulator = 0.0

    def _stand_rate(self, ss) -> float:
        """Atenciones por minuto por caja, usando los perfiles en cola."""
        scenario = self.scenario
        if not ss.queue:
            total = 0.0
            for p in scenario.profiles:
                total += (60.0 / p.service_seconds) * p.share
            return total
        total = 0.0
        for _, profile_name, service_s in ss.queue:
            eff = PICKUP_SERVICE_SECONDS if (profile_name == "pedido_movil" and ss.pickup_enabled) else service_s
            total += 60.0 / eff
        return total / len(ss.queue)
