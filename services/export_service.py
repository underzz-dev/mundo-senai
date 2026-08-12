import csv
from pathlib import Path
from typing import Iterable, Union

from models.models import AttendanceRecord


class ExportService:
    """Responsável por exportar registros de presença para CSV."""

    def export_records(
        self,
        records: Iterable[AttendanceRecord],
        output_path: Union[str, Path],
    ) -> Path:

        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as arquivo:

            writer = csv.writer(arquivo)

            writer.writerow([
                "pessoa_id",
                "nome",
                "data",
                "hora",
                "tipo",
                "distancia",
                "origem",
            ])

            for record in records:

                data = ""
                hora = ""

                if record.registered_at:
                    if "T" in record.registered_at:
                        data, hora = record.registered_at.split(
                            "T",
                            1,
                        )
                    else:
                        data = record.registered_at

                writer.writerow([
                    record.person_id,
                    record.person_name or "",
                    data,
                    hora,
                    record.record_type,
                    record.confidence,
                    record.origin,
                ])

        return output_path
