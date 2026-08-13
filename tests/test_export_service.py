import csv

from models.models import AttendanceRecord
from services.export_service import ExportService


def test_exportacao_csv(tmp_path):

    registros = [
        AttendanceRecord(
            person_id=1,
            person_name="Gustavo",
            registered_at="2026-08-12T08:00:00",
            record_type="entrada",
            distance=42.5,
            origin="camera_0",
        ),

        AttendanceRecord(
            person_id=1,
            person_name="Gustavo",
            registered_at="2026-08-12T17:00:00",
            record_type="saida",
            distance=40.2,
            origin="camera_0",
        ),
    ]

    destino = (
        tmp_path
        /
        "exports"
        /
        "historico.csv"
    )

    service = ExportService()

    resultado = service.export_records(
        registros,
        destino,
    )

    assert resultado.exists()

    with resultado.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as arquivo:

        linhas = list(
            csv.DictReader(arquivo)
        )

    assert len(linhas) == 2

    assert linhas[0]["nome"] == "Gustavo"
    assert linhas[0]["data"] == "2026-08-12"
    assert linhas[0]["hora"] == "08:00:00"
    assert linhas[0]["tipo"] == "entrada"

    assert linhas[1]["tipo"] == "saida"
