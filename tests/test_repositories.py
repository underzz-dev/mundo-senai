import pytest
from database import DatabaseManager
from models import Person, AttendanceRecord
from repositories import PersonRepository, AttendanceRepository

@pytest.fixture
def conn(tmp_path):
    db_file = tmp_path / "test_repo.db"
    db_manager = DatabaseManager(db_file)
    connection = db_manager.get_connection()
    yield connection
    db_manager.close()

def test_person_repository_crud(conn):
    person_repo = PersonRepository(conn)

    # 1. Create
    p1 = Person(name="Alice Silva", identifier="MAT123")
    saved_p1 = person_repo.create(p1)
    assert saved_p1.id is not None
    assert saved_p1.name == "Alice Silva"

    # 2. Get by ID & Get by Name & Get by Identifier
    assert person_repo.get_by_id(saved_p1.id).name == "Alice Silva"
    assert person_repo.get_by_name("alice silva").id == saved_p1.id
    assert person_repo.get_by_identifier("mat123").id == saved_p1.id

    # 3. Disable
    assert person_repo.disable(saved_p1.id) is True
    disabled_p1 = person_repo.get_by_id(saved_p1.id)
    assert disabled_p1.active is False

    # 4. List Active vs All
    p2 = Person(name="Bob Souza", identifier="MAT456")
    person_repo.create(p2)

    active_list = person_repo.list_all(active_only=True)
    all_list = person_repo.list_all(active_only=False)
    assert len(active_list) == 1
    assert len(all_list) == 2
    assert active_list[0].name == "Bob Souza"

def test_attendance_repository_operations(conn):
    person_repo = PersonRepository(conn)
    attendance_repo = AttendanceRepository(conn)

    # Criar pessoa
    p = person_repo.create(Person(name="Carlos Lima"))

    # Criar primeiro registro (entrada)
    rec1 = AttendanceRecord(
        person_id=p.id,
        record_type="entrada",
        confidence=45.2,
        origin="camera_0",
    )
    saved_rec1 = attendance_repo.create(rec1)
    assert saved_rec1.id is not None
    assert saved_rec1.record_type == "entrada"

    # Criar segundo registro (saida)
    rec2 = AttendanceRecord(
        person_id=p.id,
        record_type="saida",
        confidence=48.0,
        origin="camera_0",
    )
    attendance_repo.create(rec2)

    # Verificar ultimo registro
    last_rec = attendance_repo.get_last_by_person(p.id)
    assert last_rec is not None
    assert last_rec.record_type == "saida"
    assert last_rec.person_name == "Carlos Lima"

    # Verificar listagem recente
    recent = attendance_repo.list_recent(limit=10)
    assert len(recent) == 2

    # Count hoje
    assert attendance_repo.count_today() == 2

    # Clear history
    deleted_count = attendance_repo.clear_history()
    assert deleted_count == 2
    assert attendance_repo.count_today() == 0


def test_update_normaliza_matricula(tmp_path):
    from database.database import DatabaseManager
    from models.models import Person
    from repositories.person_repository import PersonRepository

    db = DatabaseManager(
        tmp_path / "update_normalizacao.db"
    )

    repo = PersonRepository(
        db.get_connection()
    )

    pessoa = repo.create(
        Person(
            name="Gustavo",
            identifier="MAT001",
        )
    )

    pessoa.identifier = " mat002 "

    assert repo.update(pessoa) is True

    atualizada = repo.get_by_id(
        pessoa.id
    )

    assert atualizada is not None
    assert atualizada.identifier == "MAT002"

    db.close()


def test_update_traduz_matricula_duplicada(
    tmp_path
):
    from database.database import DatabaseManager
    from exceptions import DuplicateIdentifierError
    from models.models import Person
    from repositories.person_repository import PersonRepository

    db = DatabaseManager(
        tmp_path / "update_duplicado.db"
    )

    repo = PersonRepository(
        db.get_connection()
    )

    repo.create(
        Person(
            name="Pessoa 1",
            identifier="MAT001",
        )
    )

    pessoa_2 = repo.create(
        Person(
            name="Pessoa 2",
            identifier="MAT002",
        )
    )

    pessoa_2.identifier = " mat001 "

    with pytest.raises(
        DuplicateIdentifierError
    ):
        repo.update(
            pessoa_2
        )

    db.close()
