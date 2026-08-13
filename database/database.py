import sqlite3
import logging
from pathlib import Path
from typing import Union
from exceptions import DatabaseMigrationError

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de conexão, tabelas e migrações do banco de dados SQLite."""

    def __init__(self, db_path: Union[str, Path]):
        db_path = Path(db_path)

        if str(db_path) != ":memory:":
            db_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

        self.db_path = str(db_path)
        self._conn = None
        self.connect()

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            # journal_mode = WAL não funciona bem em conexões :memory:
            if self.db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode = WAL;")
            self.init_db()
        return self._conn

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            return self.connect()
        return self._conn

    def init_db(self):
        """Cria as tabelas e índices se não existirem e executa migrações simples."""
        with self._conn:
            # Tabela de pessoas
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pessoas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    matricula TEXT UNIQUE,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );
                """
            )

            # Tabela de registros
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pessoa_id INTEGER NOT NULL,
                    registrado_em TEXT NOT NULL,
                    tipo TEXT NOT NULL DEFAULT 'entrada',
                    distancia REAL NOT NULL,
                    origem TEXT NOT NULL DEFAULT 'camera_0',
                    FOREIGN KEY(pessoa_id) REFERENCES pessoas(id) ON DELETE CASCADE
                );
                """
            )

        # Migrações para bancos já existentes com esquema antigo antes de criar os índices
        self._migrate_db()

        # Antes de criar índices UNIQUE novos, verifica se
        # bancos antigos já possuem dados conflitantes.
        self._validate_identifier_conflicts()

        with self._conn:
            # Índices
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_registros_data ON registros(registrado_em DESC);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_registros_pessoa ON registros(pessoa_id, registrado_em DESC);"
            )
            # Recria o índice para garantir unicidade
            # independentemente de maiúsculas/minúsculas.
            self._conn.execute(
                "DROP INDEX IF EXISTS idx_pessoas_matricula;"
            )

            self._conn.execute(
                """
                CREATE UNIQUE INDEX idx_pessoas_matricula
                ON pessoas(trim(matricula) COLLATE NOCASE)
                WHERE matricula IS NOT NULL
                  AND trim(matricula) != '';
                """
            )

    def _migrate_db(self):
        """Verifica se colunas adicionais faltam em esquemas antigos e aplica ALTER TABLE."""
        cursor = self._conn.cursor()

        # Verifica colunas da tabela pessoas
        cursor.execute("PRAGMA table_info(pessoas);")
        pessoas_cols = {row["name"] for row in cursor.fetchall()}

        with self._conn:
            if "matricula" not in pessoas_cols:
                logger.info("Migração: Adicionando coluna 'matricula' em 'pessoas'")
                cursor.execute("ALTER TABLE pessoas ADD COLUMN matricula TEXT;")
            if "ativo" not in pessoas_cols:
                logger.info("Migração: Adicionando coluna 'ativo' em 'pessoas'")
                cursor.execute("ALTER TABLE pessoas ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1;")
            if "atualizado_em" not in pessoas_cols:
                logger.info("Migração: Adicionando coluna 'atualizado_em' em 'pessoas'")
                cursor.execute("ALTER TABLE pessoas ADD COLUMN atualizado_em TEXT DEFAULT '';")
                cursor.execute("UPDATE pessoas SET atualizado_em = criado_em WHERE atualizado_em = '' OR atualizado_em IS NULL;")

        # Verifica colunas da tabela registros
        cursor.execute("PRAGMA table_info(registros);")
        registros_cols = {row["name"] for row in cursor.fetchall()}

        with self._conn:
            if "tipo" not in registros_cols:
                logger.info("Migração: Adicionando coluna 'tipo' em 'registros'")
                cursor.execute("ALTER TABLE registros ADD COLUMN tipo TEXT NOT NULL DEFAULT 'entrada';")
            if "origem" not in registros_cols:
                logger.info("Migração: Adicionando coluna 'origem' em 'registros'")
                cursor.execute("ALTER TABLE registros ADD COLUMN origem TEXT NOT NULL DEFAULT 'camera_0';")

    def _validate_identifier_conflicts(self):
        """
        Detecta matrículas duplicadas ignorando
        maiúsculas/minúsculas e espaços externos.

        Nenhum dado é alterado automaticamente.
        """

        rows = self._conn.execute(
            """
            SELECT
                lower(trim(matricula)) AS chave,
                COUNT(*) AS total,
                GROUP_CONCAT(matricula, ', ') AS valores
            FROM pessoas
            WHERE matricula IS NOT NULL
              AND trim(matricula) != ''
            GROUP BY lower(trim(matricula))
            HAVING COUNT(*) > 1;
            """
        ).fetchall()

        if not rows:
            return

        conflitos = "; ".join(
            row["valores"]
            for row in rows
        )

        raise DatabaseMigrationError(
            "Existem matrículas conflitantes no banco: "
            f"{conflitos}. "
            "Nenhum dado foi alterado."
        )

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
