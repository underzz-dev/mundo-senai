import sqlite3
from typing import Optional, List
from datetime import datetime
from models.models import AttendanceRecord

class AttendanceRepository:
    """Repositório responsável pelo acesso e persistência da tabela 'registros'."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _row_to_record(self, row: sqlite3.Row) -> AttendanceRecord:
        person_name = row["nome"] if "nome" in row.keys() else None
        return AttendanceRecord(
            id=row["id"],
            person_id=row["pessoa_id"],
            registered_at=row["registrado_em"],
            record_type=row["tipo"],
            distance=float(row["distancia"]),
            origin=row["origem"],
            person_name=person_name,
        )

    def create(self, record: AttendanceRecord) -> AttendanceRecord:
        if not record.registered_at:
            record.registered_at = datetime.now().isoformat(timespec="seconds")

        cursor = self.conn.execute(
            """
            INSERT INTO registros (pessoa_id, registrado_em, tipo, distancia, origem)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.person_id,
                record.registered_at,
                record.record_type,
                record.distance,
                record.origin,
            ),
        )
        self.conn.commit()
        record.id = int(cursor.lastrowid)
        return record

    def get_last_by_person(self, person_id: int) -> Optional[AttendanceRecord]:
        row = self.conn.execute(
            """
            SELECT r.*, p.nome
            FROM registros r
            JOIN pessoas p ON p.id = r.pessoa_id
            WHERE r.pessoa_id = ?
            ORDER BY r.registrado_em DESC, r.id DESC
            LIMIT 1;
            """,
            (person_id,),
        ).fetchone()

        if not row:
            return None
        return self._row_to_record(row)

    def list_recent(self, limit: int = 50) -> List[AttendanceRecord]:
        rows = self.conn.execute(
            """
            SELECT r.*, p.nome
            FROM registros r
            JOIN pessoas p ON p.id = r.pessoa_id
            ORDER BY r.registrado_em DESC, r.id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_by_person(self, person_id: int, limit: int = 50) -> List[AttendanceRecord]:
        rows = self.conn.execute(
            """
            SELECT r.*, p.nome
            FROM registros r
            JOIN pessoas p ON p.id = r.pessoa_id
            WHERE r.pessoa_id = ?
            ORDER BY r.registrado_em DESC, r.id DESC
            LIMIT ?;
            """,
            (person_id, limit),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]


    def list_by_date(
        self,
        date: str,
        limit: int = 200
    ) -> List[AttendanceRecord]:
        """Lista registros de uma data no formato YYYY-MM-DD."""

        rows = self.conn.execute(
            """
            SELECT r.*, p.nome
            FROM registros r
            JOIN pessoas p ON p.id = r.pessoa_id
            WHERE substr(r.registrado_em, 1, 10) = ?
            ORDER BY r.registrado_em DESC, r.id DESC
            LIMIT ?;
            """,
            (date, limit),
        ).fetchall()

        return [
            self._row_to_record(row)
            for row in rows
        ]

    def list_by_period(
        self,
        start_date: str,
        end_date: str,
        limit: int = 500
    ) -> List[AttendanceRecord]:
        """
        Lista registros entre duas datas,
        inclusive.

        Datas no formato YYYY-MM-DD.
        """

        rows = self.conn.execute(
            """
            SELECT r.*, p.nome
            FROM registros r
            JOIN pessoas p ON p.id = r.pessoa_id
            WHERE substr(r.registrado_em, 1, 10)
                  BETWEEN ? AND ?
            ORDER BY r.registrado_em DESC, r.id DESC
            LIMIT ?;
            """,
            (
                start_date,
                end_date,
                limit,
            ),
        ).fetchall()

        return [
            self._row_to_record(row)
            for row in rows
        ]

    def count_today(self) -> int:
        hoje = datetime.now().date().isoformat()
        row = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM registros
            WHERE substr(registrado_em, 1, 10) = ?;
            """,
            (hoje,),
        ).fetchone()
        return int(row[0]) if row else 0

    def clear_history(self) -> int:
        cursor = self.conn.execute("DELETE FROM registros;")
        self.conn.commit()
        return cursor.rowcount
