from datetime import datetime
from numbers import Real
from math import isfinite
from pathlib import Path
from threading import RLock
from typing import Optional, Union

from config import DB_PATH, EXPORTS_DIR
from database.database import DatabaseManager
from repositories.person_repository import PersonRepository
from repositories.attendance_repository import AttendanceRepository
from services.attendance_service import AttendanceService
from services.export_service import ExportService
from models import Person
from exceptions import ValidationError


class FacePointBackend:
    """
    Interface pública do backend do FacePoint.

    Reconhecimento facial e interface gráfica devem utilizar
    esta classe em vez de acessar SQLite ou repositories diretamente.
    """

    def __init__(
        self,
        db_path: Union[str, Path] = DB_PATH,
        cooldown_seconds: Optional[int] = None,
    ):
        if cooldown_seconds is not None:
            if (
                isinstance(cooldown_seconds, bool)
                or not isinstance(cooldown_seconds, int)
                or cooldown_seconds <= 0
            ):
                raise ValidationError(
                    "O cooldown deve ser um inteiro positivo."
                )

        self._lock = RLock()

        self._db = DatabaseManager(db_path)

        conn = self._db.get_connection()

        self._person_repo = PersonRepository(conn)
        self._attendance_repo = AttendanceRepository(conn)

        if cooldown_seconds is None:
            self._attendance_service = AttendanceService(
                self._person_repo,
                self._attendance_repo,
            )
        else:
            self._attendance_service = AttendanceService(
                self._person_repo,
                self._attendance_repo,
                cooldown_seconds=cooldown_seconds,
            )

        self._export_service = ExportService()

    @staticmethod
    def _validar_pessoa_id(
        pessoa_id: int
    ) -> int:
        """
        Valida IDs de pessoas recebidos pela API pública.
        """

        if (
            isinstance(pessoa_id, bool)
            or not isinstance(pessoa_id, int)
            or pessoa_id <= 0
        ):
            raise ValidationError(
                "O ID da pessoa deve ser um inteiro positivo."
            )

        return pessoa_id

    @staticmethod
    def _validar_data(
        data: str
    ) -> str:
        """
        Valida datas no formato YYYY-MM-DD.
        """

        if not isinstance(data, str):
            raise ValidationError(
                "A data deve estar no formato YYYY-MM-DD."
            )

        data = data.strip()

        try:
            parsed = datetime.strptime(
                data,
                "%Y-%m-%d"
            )
        except ValueError as exc:
            raise ValidationError(
                "A data deve estar no formato YYYY-MM-DD e ser válida."
            ) from exc

        # Garante exatamente YYYY-MM-DD.
        if parsed.strftime("%Y-%m-%d") != data:
            raise ValidationError(
                "A data deve estar no formato YYYY-MM-DD."
            )

        return data

    @staticmethod
    def _validar_limite(
        limite: int
    ) -> int:
        """
        Valida limites usados em consultas.

        Deve ser um inteiro positivo.
        """

        if (
            isinstance(limite, bool)
            or not isinstance(limite, int)
            or limite <= 0
        ):
            raise ValidationError(
                "O limite deve ser um inteiro positivo."
            )

        return limite

    # ======================================================
    # PESSOAS
    # ======================================================

    def cadastrar_pessoa(
        self,
        nome: str,
        matricula: Optional[str] = None,
    ):
        if not isinstance(nome, str) or not nome.strip():
            raise ValidationError(
                "O nome da pessoa é obrigatório."
            )

        nome = " ".join(
            nome.strip().split()
        )

        return self._attendance_service.register_person(
            name=nome,
            identifier=matricula,
        )

    def atualizar_pessoa(
        self,
        pessoa_id: int,
        nome: str,
        matricula: Optional[str] = None,
    ) -> bool:
        pessoa_id = self._validar_pessoa_id(
            pessoa_id
        )

        if not isinstance(nome, str) or not nome.strip():
            raise ValidationError(
                "O nome da pessoa é obrigatório."
            )

        nome = " ".join(
            nome.strip().split()
        )

        return self._attendance_service.update_person(
            person_id=pessoa_id,
            name=nome,
            identifier=matricula,
        )

    def obter_pessoa(
        self,
        pessoa_id: int,
    ) -> Optional[Person]:
        pessoa_id = self._validar_pessoa_id(
            pessoa_id
        )

        return self._person_repo.get_by_id(
            pessoa_id
        )

    def listar_pessoas(
        self,
        incluir_inativas: bool = False,
    ):
        if not isinstance(incluir_inativas, bool):
            raise ValidationError(
                "O parâmetro incluir_inativas deve ser booleano."
            )

        return self._person_repo.list_all(
            active_only=not incluir_inativas
        )

    def desativar_pessoa(
        self,
        pessoa_id: int,
    ) -> bool:
        pessoa_id = self._validar_pessoa_id(
            pessoa_id
        )

        return self._attendance_service.disable_person(
            pessoa_id
        )

    def reativar_pessoa(
        self,
        pessoa_id: int,
    ) -> bool:
        pessoa_id = self._validar_pessoa_id(
            pessoa_id
        )

        return self._attendance_service.enable_person(
            pessoa_id
        )

    # ======================================================
    # PONTO
    # ======================================================

    def registrar_presenca(
        self,
        pessoa_id: int,
        distancia: float,
        origem: str = "camera_0",
        ignorar_cooldown: bool = False,
    ):
        pessoa_id = self._validar_pessoa_id(
            pessoa_id
        )

        if (
            isinstance(distancia, bool)
            or not isinstance(distancia, Real)
            or not isfinite(float(distancia))
        ):
            raise ValidationError(
                "A distância deve ser um número real e finito."
            )

        distancia = float(distancia)

        if not isinstance(origem, str) or not origem.strip():
            raise ValidationError(
                "A origem do registro deve ser um texto não vazio."
            )

        origem = origem.strip()

        if not isinstance(ignorar_cooldown, bool):
            raise ValidationError(
                "O parâmetro ignorar_cooldown deve ser booleano."
            )

        with self._lock:
            return self._attendance_service.register_attendance(
                person_id=pessoa_id,
                distance=distancia,
                origin=origem,
                override_cooldown=ignorar_cooldown,
            )

    # ======================================================
    # HISTÓRICO
    # ======================================================

    def listar_historico(
        self,
        limite: int = 50,
    ):
        limite = self._validar_limite(
            limite
        )

        return self._attendance_repo.list_recent(
            limit=limite
        )

    def historico_pessoa(
        self,
        pessoa_id: int,
        limite: int = 50,
    ):
        pessoa_id = self._validar_pessoa_id(
            pessoa_id
        )

        limite = self._validar_limite(
            limite
        )

        return self._attendance_repo.list_by_person(
            pessoa_id,
            limit=limite,
        )

    def historico_data(
        self,
        data: str,
        limite: int = 200,
    ):
        data = self._validar_data(
            data
        )

        limite = self._validar_limite(
            limite
        )

        return self._attendance_repo.list_by_date(
            data,
            limit=limite,
        )

    def historico_periodo(
        self,
        inicio: str,
        fim: str,
        limite: int = 500,
    ):
        inicio = self._validar_data(
            inicio
        )

        fim = self._validar_data(
            fim
        )

        if inicio > fim:
            raise ValidationError(
                "A data de início não pode ser posterior à data de fim."
            )

        limite = self._validar_limite(
            limite
        )

        return self._attendance_repo.list_by_period(
            inicio,
            fim,
            limit=limite,
        )

    # ======================================================
    # EXPORTAÇÃO
    # ======================================================

    def exportar_historico(
        self,
        caminho: Optional[Union[str, Path]] = None,
        limite: int = 10000,
    ) -> Path:

        limite = self._validar_limite(
            limite
        )

        registros = self._attendance_repo.list_recent(
            limit=limite
        )

        if caminho is None:
            caminho = (
                EXPORTS_DIR
                /
                "historico_facepoint.csv"
            )

        return self._export_service.export_records(
            registros,
            caminho,
        )

    # ======================================================
    # MÉTRICAS
    # ======================================================

    def metricas(self):
        return (
            self._attendance_service
            .get_dashboard_metrics()
        )

    # ======================================================
    # ENCERRAMENTO
    # ======================================================

    def fechar(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.fechar()
