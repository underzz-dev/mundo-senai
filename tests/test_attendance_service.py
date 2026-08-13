from datetime import datetime
from types import SimpleNamespace

from services.attendance_service import AttendanceService


class FakePersonRepository:
    def __init__(self, people=None):
        self.people = people or {}

    def get_by_id(self, person_id):
        return self.people.get(person_id)


class FakeAttendanceRepository:
    def __init__(self, last_record=None):
        self.last_record = last_record
        self.created = []

    def get_last_by_person(self, person_id):
        return self.last_record

    def create(self, record):
        self.created.append(record)
        self.last_record = record
        return record


def pessoa(
    person_id=1,
    name="Gustavo",
    active=True
):
    return SimpleNamespace(
        id=person_id,
        name=name,
        active=active
    )


def test_pessoa_inexistente():
    service = AttendanceService(
        FakePersonRepository(),
        FakeAttendanceRepository()
    )

    result = service.register_attendance(
        person_id=999,
        distance=40.0
    )

    assert result.success is False
    assert result.registered is False


def test_pessoa_inativa():
    person_repo = FakePersonRepository({
        1: pessoa(active=False)
    })

    attendance_repo = FakeAttendanceRepository()

    service = AttendanceService(
        person_repo,
        attendance_repo
    )

    result = service.register_attendance(
        1,
        40.0
    )

    assert result.success is False
    assert result.registered is False
    assert attendance_repo.created == []


def test_primeiro_registro_e_entrada():
    person_repo = FakePersonRepository({
        1: pessoa()
    })

    attendance_repo = FakeAttendanceRepository()

    service = AttendanceService(
        person_repo,
        attendance_repo
    )

    result = service.register_attendance(
        1,
        35.0
    )

    assert result.success is True
    assert result.registered is True
    assert result.record_type == "entrada"


def test_segundo_registro_e_saida():
    person_repo = FakePersonRepository({
        1: pessoa()
    })

    attendance_repo = FakeAttendanceRepository()

    service = AttendanceService(
        person_repo,
        attendance_repo
    )

    primeiro = service.register_attendance(
        1,
        35.0
    )

    segundo = service.register_attendance(
        1,
        36.0,
        override_cooldown=True
    )

    assert primeiro.record_type == "entrada"
    assert segundo.record_type == "saida"


def test_terceiro_registro_volta_para_entrada():
    person_repo = FakePersonRepository({
        1: pessoa()
    })

    attendance_repo = FakeAttendanceRepository()

    service = AttendanceService(
        person_repo,
        attendance_repo
    )

    primeiro = service.register_attendance(
        1,
        30.0
    )

    segundo = service.register_attendance(
        1,
        31.0,
        override_cooldown=True
    )

    terceiro = service.register_attendance(
        1,
        32.0,
        override_cooldown=True
    )

    assert primeiro.record_type == "entrada"
    assert segundo.record_type == "saida"
    assert terceiro.record_type == "entrada"


def test_cooldown_bloqueia_registro():
    registro_recente = SimpleNamespace(
        person_id=1,
        registered_at=datetime.now().isoformat(
            timespec="seconds"
        ),
        record_type="entrada",
        distance=30.0,
        origin="camera_0"
    )

    person_repo = FakePersonRepository({
        1: pessoa()
    })

    attendance_repo = FakeAttendanceRepository(
        registro_recente
    )

    service = AttendanceService(
        person_repo,
        attendance_repo,
        cooldown_seconds=60
    )

    result = service.register_attendance(
        1,
        32.0
    )

    assert result.success is True
    assert result.registered is False
    assert result.cooldown_remaining_seconds > 0
    assert attendance_repo.created == []


def test_override_ignora_cooldown():
    registro_recente = SimpleNamespace(
        person_id=1,
        registered_at=datetime.now().isoformat(
            timespec="seconds"
        ),
        record_type="entrada",
        distance=30.0,
        origin="camera_0"
    )

    person_repo = FakePersonRepository({
        1: pessoa()
    })

    attendance_repo = FakeAttendanceRepository(
        registro_recente
    )

    service = AttendanceService(
        person_repo,
        attendance_repo
    )

    result = service.register_attendance(
        1,
        33.0,
        override_cooldown=True
    )

    assert result.registered is True
    assert result.record_type == "saida"
    assert len(attendance_repo.created) == 1
