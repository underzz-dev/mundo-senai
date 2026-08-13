import logging
from datetime import datetime
from typing import Optional, List, Union
from pathlib import Path

from config import COOLDOWN_SECONDS
from models.models import Person, AttendanceRecord, AttendanceResult
from repositories.person_repository import PersonRepository
from repositories.attendance_repository import AttendanceRepository

logger = logging.getLogger(__name__)

class AttendanceService:
    """Serviço centralizador de regras de negócio para presença e marcação de ponto."""

    def __init__(
        self,
        person_repo: PersonRepository,
        attendance_repo: AttendanceRepository,
        cooldown_seconds: int = COOLDOWN_SECONDS,
    ):
        self.person_repo = person_repo
        self.attendance_repo = attendance_repo
        self.cooldown_seconds = cooldown_seconds

    def _determine_next_record_type(self, last_record: Optional[AttendanceRecord]) -> str:
        """Determina se o próximo registro deve ser 'entrada' ou 'saida'.
        
        Pode ser estendido/substituído no futuro por regras baseadas em horários.
        """
        if not last_record or not last_record.record_type:
            return "entrada"
        if last_record.record_type.lower() == "entrada":
            return "saida"
        return "entrada"

    def register_attendance(
        self,
        person_id: int,
        distance: float,
        origin: str = "camera_0",
        override_cooldown: bool = False,
    ) -> AttendanceResult:
        """Executa a verificação e registro de presença para uma pessoa.
        
        Fluxo:
        1. Verifica se a pessoa existe
        2. Verifica se a pessoa está ativa
        3. Verifica último registro e aplica cooldown
        4. Determina tipo (entrada/saída)
        5. Registra no banco
        6. Retorna resultado estruturado
        """
        # 1. Verificar se a pessoa existe
        person = self.person_repo.get_by_id(person_id)
        if not person:
            logger.warning("Tentativa de registro para pessoa inexistente: id=%s", person_id)
            return AttendanceResult(
                success=False,
                registered=False,
                message=f"Pessoa com ID {person_id} não encontrada.",
            )

        # 2. Verificar se a pessoa está ativa
        if not person.active:
            logger.warning("Tentativa de registro para pessoa inativa: id=%s, nome=%s", person.id, person.name)
            return AttendanceResult(
                success=False,
                registered=False,
                person=person,
                message=f"A pessoa '{person.name}' está desativada no sistema.",
            )

        # 3. Verificar último registro e aplicar cooldown
        last_record = self.attendance_repo.get_last_by_person(person_id)
        now = datetime.now()

        if last_record and not override_cooldown:
            try:
                last_time = datetime.fromisoformat(last_record.registered_at)
                elapsed_seconds = (now - last_time).total_seconds()
                if elapsed_seconds < self.cooldown_seconds:
                    remaining = self.cooldown_seconds - elapsed_seconds
                    logger.info(
                        "Registro ignorado por cooldown (restam %.1fs): %s",
                        remaining,
                        person.name,
                    )
                    return AttendanceResult(
                        success=True,
                        registered=False,
                        person=person,
                        timestamp=last_record.registered_at,
                        cooldown_remaining_seconds=round(remaining, 1),
                        message=f"Registro recente. Aguarde mais {int(remaining) + 1}s para novo ponto.",
                    )
            except (ValueError, TypeError) as e:
                logger.error("Erro ao processar data do último registro: %s", e)

        # 4. Determinar tipo (entrada/saída)
        next_type = self._determine_next_record_type(last_record)

        # 5. Criar registro no banco
        now_str = now.isoformat(timespec="seconds")
        new_record = AttendanceRecord(
            person_id=person.id,
            registered_at=now_str,
            record_type=next_type,
            distance=float(distance),
            origin=origin,
        )
        saved_record = self.attendance_repo.create(new_record)
        logger.info(
            "Presença (%s) registrada com sucesso para %s (distância: %.1f)",
            next_type,
            person.name,
            distance,
        )

        # 6. Retornar resultado estruturado
        return AttendanceResult(
            success=True,
            registered=True,
            person=person,
            record_type=next_type,
            timestamp=now_str,
            distance=float(distance),
            message=f"Presença ({next_type}) registrada com sucesso para {person.name}.",
        )

    def register_person(self, name: str, identifier: Optional[str] = None) -> Person:
        person = Person(name=name, identifier=identifier)
        saved = self.person_repo.create(person)
        logger.info("Nova pessoa cadastrada: %s (id=%s)", saved.name, saved.id)
        return saved

    def get_or_create_person(self, name: str) -> Person:
        return self.person_repo.get_or_create_by_name(name)

    def disable_person(self, person_id: int) -> bool:
        success = self.person_repo.disable(person_id)
        if success:
            logger.info("Pessoa id=%s desativada com sucesso.", person_id)
        return success

    def enable_person(self, person_id: int) -> bool:
        success = self.person_repo.enable(person_id)
        if success:
            logger.info("Pessoa id=%s reativada com sucesso.", person_id)
        return success

    def list_active_people(self) -> List[Person]:
        return self.person_repo.list_all(active_only=True)

    def list_recent_records(self, limit: int = 50) -> List[AttendanceRecord]:
        return self.attendance_repo.list_recent(limit=limit)

    def get_dashboard_metrics(self) -> dict:
        """Retorna métricas consolidadas para a interface gráfica."""
        return {
            "total_pessoas": self.person_repo.count_active(),
            "registros_hoje": self.attendance_repo.count_today(),
        }
