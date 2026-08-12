from database.database import DatabaseManager
from models.models import Person, AttendanceRecord
from repositories.person_repository import PersonRepository
from repositories.attendance_repository import AttendanceRepository


def test_historico_por_data_e_periodo(tmp_path):
    banco = tmp_path / "historico.db"

    db = DatabaseManager(banco)

    conn = db.get_connection()

    pessoas = PersonRepository(conn)
    registros = AttendanceRepository(conn)

    # ==========================================
    # PESSOAS
    # ==========================================

    gustavo = pessoas.create(
        Person(
            name="Gustavo",
            identifier="MAT001"
        )
    )

    ana = pessoas.create(
        Person(
            name="Ana",
            identifier="MAT002"
        )
    )

    # ==========================================
    # REGISTROS EM DATAS DIFERENTES
    # ==========================================

    registros.create(
        AttendanceRecord(
            person_id=gustavo.id,
            registered_at="2026-08-10T08:00:00",
            record_type="entrada",
            confidence=40.0,
            origin="camera_0",
        )
    )

    registros.create(
        AttendanceRecord(
            person_id=gustavo.id,
            registered_at="2026-08-10T17:00:00",
            record_type="saida",
            confidence=42.0,
            origin="camera_0",
        )
    )

    registros.create(
        AttendanceRecord(
            person_id=ana.id,
            registered_at="2026-08-11T08:30:00",
            record_type="entrada",
            confidence=38.0,
            origin="camera_0",
        )
    )

    registros.create(
        AttendanceRecord(
            person_id=ana.id,
            registered_at="2026-08-12T16:00:00",
            record_type="saida",
            confidence=39.0,
            origin="camera_0",
        )
    )

    # ==========================================
    # HISTÓRICO DE UM DIA
    # ==========================================

    dia_10 = registros.list_by_date(
        "2026-08-10"
    )

    assert len(dia_10) == 2

    assert all(
        registro.person_id == gustavo.id
        for registro in dia_10
    )

    # ==========================================
    # HISTÓRICO DE OUTRO DIA
    # ==========================================

    dia_11 = registros.list_by_date(
        "2026-08-11"
    )

    assert len(dia_11) == 1
    assert dia_11[0].person_id == ana.id
    assert dia_11[0].person_name == "Ana"

    # ==========================================
    # DATA SEM REGISTROS
    # ==========================================

    vazio = registros.list_by_date(
        "2026-08-09"
    )

    assert vazio == []

    # ==========================================
    # INTERVALO
    # ==========================================

    periodo = registros.list_by_period(
        "2026-08-10",
        "2026-08-11",
    )

    assert len(periodo) == 3

    # O dia 12 não pode aparecer
    assert all(
        not registro.registered_at.startswith(
            "2026-08-12"
        )
        for registro in periodo
    )

    # ==========================================
    # HISTÓRICO POR PESSOA
    # ==========================================

    historico_gustavo = (
        registros.list_by_person(
            gustavo.id
        )
    )

    assert len(historico_gustavo) == 2

    assert historico_gustavo[0].record_type == "saida"
    assert historico_gustavo[1].record_type == "entrada"

    db.close()
