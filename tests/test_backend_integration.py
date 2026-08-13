from database.database import DatabaseManager
from repositories.person_repository import PersonRepository
from repositories.attendance_repository import AttendanceRepository
from services.attendance_service import AttendanceService


def criar_backend(db_path):
    db = DatabaseManager(db_path)

    conn = db.get_connection()

    person_repo = PersonRepository(conn)
    attendance_repo = AttendanceRepository(conn)

    service = AttendanceService(
        person_repo,
        attendance_repo,
        cooldown_seconds=60,
    )

    return (
        db,
        person_repo,
        attendance_repo,
        service,
    )


def test_fluxo_completo_backend_sqlite(tmp_path):
    banco = tmp_path / "facepoint_test.db"

    (
        db,
        person_repo,
        attendance_repo,
        service,
    ) = criar_backend(banco)

    # =========================================
    # 1. CADASTRAR PESSOA
    # =========================================

    pessoa = service.register_person(
        name="Gustavo",
        identifier="MAT001",
    )

    assert pessoa.id is not None
    assert pessoa.name == "Gustavo"
    assert pessoa.identifier == "MAT001"
    assert pessoa.active is True

    # Confirma que realmente foi salva no SQLite
    pessoa_banco = person_repo.get_by_id(
        pessoa.id
    )

    assert pessoa_banco is not None
    assert pessoa_banco.name == "Gustavo"

    # =========================================
    # 2. PRIMEIRO PONTO = ENTRADA
    # =========================================

    entrada = service.register_attendance(
        person_id=pessoa.id,
        distance=42.5,
        origin="camera_teste",
    )

    assert entrada.success is True
    assert entrada.registered is True
    assert entrada.record_type == "entrada"

    # =========================================
    # 3. COOLDOWN
    # =========================================

    duplicado = service.register_attendance(
        person_id=pessoa.id,
        distance=43.0,
        origin="camera_teste",
    )

    assert duplicado.success is True
    assert duplicado.registered is False
    assert (
        duplicado.cooldown_remaining_seconds
        >
        0
    )

    # Banco ainda deve conter somente 1 ponto
    registros = attendance_repo.list_by_person(
        pessoa.id
    )

    assert len(registros) == 1
    assert registros[0].record_type == "entrada"

    # =========================================
    # 4. SEGUNDO PONTO = SAÍDA
    # =========================================

    saida = service.register_attendance(
        person_id=pessoa.id,
        distance=44.0,
        origin="camera_teste",
        override_cooldown=True,
    )

    assert saida.success is True
    assert saida.registered is True
    assert saida.record_type == "saida"

    registros = attendance_repo.list_by_person(
        pessoa.id
    )

    assert len(registros) == 2

    assert registros[0].record_type == "saida"
    assert registros[1].record_type == "entrada"

    # =========================================
    # 5. DESATIVAR PESSOA
    # =========================================

    assert service.disable_person(
        pessoa.id
    ) is True

    bloqueado = service.register_attendance(
        person_id=pessoa.id,
        distance=40.0,
        override_cooldown=True,
    )

    assert bloqueado.success is False
    assert bloqueado.registered is False

    # Nenhum novo registro deve ter sido criado
    registros = attendance_repo.list_by_person(
        pessoa.id
    )

    assert len(registros) == 2

    # =========================================
    # 6. FECHAR BANCO
    # =========================================

    db.close()

    # =========================================
    # 7. ABRIR NOVAMENTE
    # =========================================

    (
        db2,
        person_repo2,
        attendance_repo2,
        service2,
    ) = criar_backend(banco)

    # Pessoa deve continuar existindo
    pessoa_recarregada = (
        person_repo2.get_by_id(
            pessoa.id
        )
    )

    assert pessoa_recarregada is not None
    assert pessoa_recarregada.name == "Gustavo"
    assert pessoa_recarregada.active is False

    # Registros também precisam continuar no banco
    registros_recarregados = (
        attendance_repo2.list_by_person(
            pessoa.id
        )
    )

    assert len(
        registros_recarregados
    ) == 2

    assert (
        registros_recarregados[0]
        .record_type
        ==
        "saida"
    )

    assert (
        registros_recarregados[1]
        .record_type
        ==
        "entrada"
    )

    db2.close()
