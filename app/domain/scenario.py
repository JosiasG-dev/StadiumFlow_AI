"""
Modelos de dominio: Scenario, Stand, Sector, Phase, FanProfile.
Todas las validaciones de negocio viven aquí con model_validator de Pydantic v2.
"""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


PHASE_NAMES = Literal["antes", "primer_tiempo", "medio_tiempo", "segundo_tiempo", "salida"]
PROFILE_NAMES = Literal["compra_rapida", "compra_grupo", "pedido_movil"]

SLUG_RE = re.compile(r"^[a-z0-9_-]{3,40}$")


class Stand(BaseModel):
    """Puesto de alimentos y bebidas (P1–P10)."""

    id: str = Field(..., description="Identificador único del puesto (p. ej. 'P1')")
    name: str = Field(..., min_length=1, max_length=60)
    x: float = Field(..., description="Coordenada X en el SVG del recinto")
    y: float = Field(..., description="Coordenada Y en el SVG del recinto")
    registers_installed: int = Field(..., ge=1, le=20, description="Cajas instaladas")
    registers_open: int = Field(..., ge=0, description="Cajas abiertas al inicio")
    staff: int = Field(..., ge=1, le=50, description="Personal asignado")
    pickup_enabled: bool = Field(default=False, description="Ventana de recolección rápida activa")
    zone_capacity: int = Field(default=60, ge=1, description="Capacidad de la zona para cálculo de densidad")
    avg_ticket: float = Field(default=120.0, ge=0.0, description="Ticket promedio sintético (MXN)")

    @model_validator(mode="after")
    def validate_registers_staff(self) -> "Stand":
        if self.registers_open > self.registers_installed:
            raise ValueError(
                f"Puesto {self.id}: cajas_abiertas ({self.registers_open}) "
                f"no puede superar cajas_instaladas ({self.registers_installed})."
            )
        if self.registers_open > self.staff:
            raise ValueError(
                f"Puesto {self.id}: cajas_abiertas ({self.registers_open}) "
                f"no puede superar el personal ({self.staff})."
            )
        return self


class Sector(BaseModel):
    """Gradería o zona del recinto."""

    id: str = Field(..., description="Identificador único del sector (p. ej. 'S1')")
    name: str = Field(..., min_length=1, max_length=60)
    x: float = Field(..., description="Coordenada X en el SVG")
    y: float = Field(..., description="Coordenada Y en el SVG")
    share: float = Field(..., gt=0.0, le=1.0, description="Fracción del aforo en este sector")


class Phase(BaseModel):
    """Fase del evento (p. ej. medio_tiempo)."""

    name: PHASE_NAMES
    duration_min: int = Field(..., ge=1, le=180, description="Duración en minutos simulados")
    purchase_prob: float = Field(..., ge=0.0, le=2.0, description="Viajes de compra esperados por aficionado en esta fase")


class FanProfile(BaseModel):
    """Perfil de comportamiento del aficionado."""

    name: PROFILE_NAMES
    share: float = Field(..., gt=0.0, le=1.0, description="Fracción del total de aficionados")
    service_seconds: float = Field(..., gt=0.0, le=600.0, description="Segundos de atención en caja")
    patience_min: float = Field(..., gt=0.0, le=60.0, description="Paciencia máxima de espera (minutos)")


class Scenario(BaseModel):
    """Configuración completa de un escenario de simulación."""

    id: str = Field(..., description="Slug único del escenario")
    name: str = Field(..., min_length=1, max_length=120)
    event_type: str = Field(default="fútbol", max_length=60)
    attendance: int = Field(..., ge=100, le=100_000, description="Aforo atendido por los puestos")
    phases: list[Phase] = Field(..., min_length=5, max_length=5)
    stands: list[Stand] = Field(..., min_length=1, max_length=30)
    sectors: list[Sector] = Field(..., min_length=1, max_length=30)
    profiles: list[FanProfile] = Field(..., min_length=1, max_length=10)
    mobile_share: float = Field(default=0.15, ge=0.0, le=1.0, description="Fracción de pedido móvil (informativo)")
    redirect_compliance: float = Field(default=0.60, ge=0.0, le=1.0)
    anticipation_share: float = Field(default=0.0, ge=0.0, le=0.5, description="Fracción de demanda anticipada de medio tiempo")
    seed: int = Field(default=42)

    @field_validator("id")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError(
                "El id debe tener entre 3 y 40 caracteres: solo letras minúsculas, dígitos, guion o guion bajo."
            )
        return v

    @model_validator(mode="after")
    def validate_phases(self) -> "Scenario":
        names = [p.name for p in self.phases]
        required = {"antes", "primer_tiempo", "medio_tiempo", "segundo_tiempo", "salida"}
        if set(names) != required:
            raise ValueError(f"Se requieren exactamente las 5 fases: {required}. Recibidas: {names}")
        return self

    @model_validator(mode="after")
    def validate_sector_shares(self) -> "Scenario":
        total = sum(s.share for s in self.sectors)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"La suma de share de los sectores debe ser 1 ± 0.01. Actual: {total:.4f}")
        return self

    @model_validator(mode="after")
    def validate_profile_shares(self) -> "Scenario":
        total = sum(p.share for p in self.profiles)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"La suma de share de los perfiles debe ser 1 ± 0.01. Actual: {total:.4f}")
        return self
