from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime

@dataclass
class Person:
    """Entidade que representa uma pessoa cadastrada no sistema."""
    id: Optional[int] = None
    name: str = ""
    identifier: Optional[str] = None  # matrícula ou ID corporativo
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AttendanceRecord:
    """Entidade que representa um registro de presença/ponto."""
    id: Optional[int] = None
    person_id: int = 0
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    record_type: str = "entrada"  # "entrada" ou "saida"
    confidence: float = 0.0
    origin: str = "camera_0"
    person_name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AttendanceResult:
    """Estrutura padronizada de resposta das operações de registro de ponto."""
    success: bool
    registered: bool
    message: str
    person: Optional[Person] = None
    record_type: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = None
    cooldown_remaining_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.person:
            data["person"] = self.person.to_dict()
        return data
