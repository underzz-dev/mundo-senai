import sqlite3
import pytest
from database import DatabaseManager

def test_database_initialization(tmp_path):
    db_file = tmp_path / "test_facepoint.db"
    db_manager = DatabaseManager(db_file)
    conn = db_manager.get_connection()

    # Verificar tabelas
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cursor.fetchall()}
    assert "pessoas" in tables
    assert "registros" in tables

    # Verificar colunas de pessoas
    cursor.execute("PRAGMA table_info(pessoas);")
    pessoas_cols = {row["name"] for row in cursor.fetchall()}
    expected_pessoas = {"id", "nome", "matricula", "ativo", "criado_em", "atualizado_em"}
    assert expected_pessoas.issubset(pessoas_cols)

    # Verificar colunas de registros
    cursor.execute("PRAGMA table_info(registros);")
    registros_cols = {row["name"] for row in cursor.fetchall()}
    expected_registros = {"id", "pessoa_id", "registrado_em", "tipo", "distancia", "origem"}
    assert expected_registros.issubset(registros_cols)

    db_manager.close()

def test_database_migration(tmp_path):
    """Testa se o DatabaseManager consegue migrar um banco de dados antigo sem perder dados."""
    db_file = tmp_path / "old_facepoint.db"

    # Criar banco antigo manualmente
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            criado_em TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            registrado_em TEXT NOT NULL,
            distancia REAL NOT NULL
        );
    """)
    conn.execute("INSERT INTO pessoas (nome, criado_em) VALUES ('Carlos Teste', '2026-01-01T10:00:00');")
    conn.execute("INSERT INTO registros (pessoa_id, registrado_em, distancia) VALUES (1, '2026-01-01T10:05:00', 45.0);")
    conn.commit()
    conn.close()

    # Instanciar DatabaseManager no banco antigo para acionar a migração
    db_manager = DatabaseManager(db_file)
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    # Verificar que o dado antigo ainda existe
    cursor.execute("SELECT * FROM pessoas WHERE id = 1;")
    person = cursor.fetchone()
    assert person["nome"] == "Carlos Teste"
    assert person["ativo"] == 1  # valor padrão adicionado na migração

    cursor.execute("SELECT * FROM registros WHERE id = 1;")
    registro = cursor.fetchone()
    assert registro["tipo"] == "entrada"  # valor padrão adicionado na migração
    assert registro["origem"] == "camera_0"

    db_manager.close()

def test_foreign_key_constraint(tmp_path):
    """Testa se a restrição de chave estrangeira é ativada corretamente."""
    db_file = tmp_path / "fk_test.db"
    db_manager = DatabaseManager(db_file)
    conn = db_manager.get_connection()

    with pytest.raises(sqlite3.IntegrityError):
        # Tentar inserir registro com pessoa_id inexistente (999)
        conn.execute(
            "INSERT INTO registros (pessoa_id, registrado_em, tipo, distancia) VALUES (999, '2026-01-01T10:00:00', 'entrada', 30.0);"
        )

    db_manager.close()


def test_matricula_unique_case_insensitive_no_sqlite(tmp_path):
    import sqlite3

    from database.database import DatabaseManager

    banco = tmp_path / "case_insensitive.db"

    db = DatabaseManager(banco)
    conn = db.get_connection()

    conn.execute(
        """
        INSERT INTO pessoas (
            nome,
            matricula,
            ativo,
            criado_em,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            "Gustavo",
            "MAT001",
            1,
            "2026-08-12T10:00:00",
            "2026-08-12T10:00:00",
        ),
    )

    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO pessoas (
                nome,
                matricula,
                ativo,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                "Ana",
                "mat001",
                1,
                "2026-08-12T10:01:00",
                "2026-08-12T10:01:00",
            ),
        )

    db.close()


def test_migracao_detecta_matriculas_conflitantes(tmp_path):
    import sqlite3

    from database.database import DatabaseManager

    banco = tmp_path / "legacy_conflito.db"

    # Simula banco antigo
    conn = sqlite3.connect(banco)

    conn.execute(
        """
        CREATE TABLE pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            registrado_em TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'entrada',
            distancia REAL NOT NULL,
            origem TEXT NOT NULL DEFAULT 'camera_0'
        );
        """
    )

    conn.execute(
        """
        INSERT INTO pessoas
        (nome, matricula, ativo, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            "Gustavo",
            "MAT001",
            1,
            "2026-08-12T10:00:00",
            "2026-08-12T10:00:00",
        ),
    )

    conn.execute(
        """
        INSERT INTO pessoas
        (nome, matricula, ativo, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            "Ana",
            "mat001",
            1,
            "2026-08-12T10:01:00",
            "2026-08-12T10:01:00",
        ),
    )

    conn.commit()
    conn.close()

    # Banco novo não deve perder dados silenciosamente.
    import pytest
    import sqlite3

    from exceptions import DatabaseMigrationError

    with pytest.raises(
        DatabaseMigrationError,
        match="matrículas conflitantes"
    ):
        DatabaseManager(banco)


def test_banco_bloqueia_matricula_com_espacos_e_caixa_diferente(
    tmp_path
):
    import sqlite3
    from datetime import datetime

    from database.database import DatabaseManager

    db = DatabaseManager(
        tmp_path / "matricula_trim.db"
    )

    conn = db.get_connection()

    agora = datetime.now().isoformat(
        timespec="seconds"
    )

    conn.execute(
        """
        INSERT INTO pessoas (
            nome,
            matricula,
            ativo,
            criado_em,
            atualizado_em
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Pessoa 1",
            "MAT001",
            1,
            agora,
            agora,
        ),
    )

    conn.commit()

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        conn.execute(
            """
            INSERT INTO pessoas (
                nome,
                matricula,
                ativo,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Pessoa 2",
                " mat001 ",
                1,
                agora,
                agora,
            ),
        )

        conn.commit()

    db.close()
