import sqlite3
from typing import Optional, List
from datetime import datetime
from models.models import Person
from exceptions import DuplicateIdentifierError

class PersonRepository:
    """Repositório responsável pelo acesso e persistência dos dados da tabela 'pessoas'."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _normalize_identifier(
        identifier: Optional[str]
    ) -> Optional[str]:
        """
        Normaliza matrícula/identificador.

        Exemplos:
        " mat001 " -> "MAT001"
        ""         -> None
        """
        if identifier is None:
            return None

        normalized = identifier.strip().upper()

        return normalized or None

    def _row_to_person(self, row: sqlite3.Row) -> Person:
        return Person(
            id=row["id"],
            name=row["nome"],
            identifier=row["matricula"],
            active=bool(row["ativo"]),
            created_at=row["criado_em"],
            updated_at=row["atualizado_em"],
        )

    def create(self, person: Person) -> Person:
        identifier = self._normalize_identifier(
            person.identifier
        )

        if identifier:
            existing = self.get_by_identifier(
                identifier
            )

            if existing:
                raise DuplicateIdentifierError(
                    f"A matrícula '{identifier}' já está cadastrada."
                )

        person.identifier = identifier

        now = datetime.now().isoformat(timespec="seconds")
        if not person.created_at:
            person.created_at = now
        person.updated_at = now

        try:
            cursor = self.conn.execute(
                """
                INSERT INTO pessoas (nome, matricula, ativo, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    person.name.strip(),
                    person.identifier,
                    1 if person.active else 0,
                    person.created_at,
                    person.updated_at,
                ),
            )
            self.conn.commit()

        except sqlite3.IntegrityError as exc:
            if "matricula" in str(exc).lower():
                raise DuplicateIdentifierError(
                    f"A matrícula '{person.identifier}' já está cadastrada."
                ) from exc

            raise
        person.id = int(cursor.lastrowid)
        return person

    def get_by_id(self, person_id: int) -> Optional[Person]:
        row = self.conn.execute(
            "SELECT * FROM pessoas WHERE id = ?;", (person_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_person(row)

    def get_by_name(self, name: str) -> Optional[Person]:
        row = self.conn.execute(
            "SELECT * FROM pessoas WHERE lower(nome) = lower(?);", (name.strip(),)
        ).fetchone()
        if not row:
            return None
        return self._row_to_person(row)

    def get_by_identifier(self, identifier: str) -> Optional[Person]:
        identifier = self._normalize_identifier(
            identifier
        )

        if not identifier:
            return None

        row = self.conn.execute(
            """
            SELECT *
            FROM pessoas
            WHERE lower(matricula) = lower(?);
            """,
            (identifier,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_person(row)

    def get_or_create_by_name(self, name: str) -> Person:
        existing = self.get_by_name(name)
        if existing:
            return existing
        new_person = Person(name=name)
        return self.create(new_person)

    def list_all(self, active_only: bool = True) -> List[Person]:
        if active_only:
            rows = self.conn.execute(
                "SELECT * FROM pessoas WHERE ativo = 1 ORDER BY nome ASC;"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM pessoas ORDER BY nome ASC;"
            ).fetchall()
        return [self._row_to_person(row) for row in rows]

    def update(self, person: Person) -> bool:
        if not person.id:
            return False

        identifier = self._normalize_identifier(
            person.identifier
        )

        if identifier:
            existing = self.get_by_identifier(
                identifier
            )

            if (
                existing
                and existing.id != person.id
            ):
                raise DuplicateIdentifierError(
                    f"A matrícula '{identifier}' já está cadastrada."
                )

        person.identifier = identifier

        now = datetime.now().isoformat(
            timespec="seconds"
        )
        person.updated_at = now

        try:
            cursor = self.conn.execute(
                """
                UPDATE pessoas
                SET nome = ?, matricula = ?, ativo = ?, atualizado_em = ?
                WHERE id = ?;
                """,
                (
                    person.name.strip(),
                    person.identifier,
                    1 if person.active else 0,
                    person.updated_at,
                    person.id,
                ),
            )

            self.conn.commit()

        except sqlite3.IntegrityError as exc:
            mensagem = str(exc).lower()

            if (
                "matricula" in mensagem
                or "idx_pessoas_matricula" in mensagem
            ):
                raise DuplicateIdentifierError(
                    f"A matrícula '{person.identifier}' já está cadastrada."
                ) from exc

            raise

        return cursor.rowcount > 0

    def disable(self, person_id: int) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            "UPDATE pessoas SET ativo = 0, atualizado_em = ? WHERE id = ?;",
            (now, person_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def count_active(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM pessoas WHERE ativo = 1;"
        ).fetchone()
        return int(row[0]) if row else 0
