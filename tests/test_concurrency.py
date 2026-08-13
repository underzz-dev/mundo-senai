from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep

from backend import FacePointBackend


def test_backend_pode_ser_usado_em_outra_thread(tmp_path):
    """
    O backend pode ser criado em uma thread
    e consultado em outra.
    """

    backend = FacePointBackend(
        db_path=tmp_path / "thread_test.db"
    )

    backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    def consultar_backend():
        return backend.listar_pessoas()

    with ThreadPoolExecutor(max_workers=1) as executor:
        pessoas = executor.submit(
            consultar_backend
        ).result()

    assert len(pessoas) == 1
    assert pessoas[0].name == "Gustavo"

    backend.fechar()


def test_duas_threads_nao_registram_ponto_duplicado(tmp_path):
    """
    Duas chamadas simultâneas para a mesma pessoa
    não podem gerar dois registros.
    """

    backend = FacePointBackend(
        db_path=tmp_path / "race_condition.db",
        cooldown_seconds=60,
    )

    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    original_get_last = (
        backend._attendance_repo.get_last_by_person
    )

    def get_last_lento(person_id):
        ultimo = original_get_last(person_id)

        # Aumenta propositalmente a janela da race condition.
        sleep(0.05)

        return ultimo

    backend._attendance_repo.get_last_by_person = (
        get_last_lento
    )

    inicio = Barrier(2)

    def registrar():
        # As duas threads chegam aqui antes de entrar
        # na operação pública do backend.
        inicio.wait(timeout=2)

        return backend.registrar_presenca(
            pessoa_id=pessoa.id,
            distancia=42.0,
            origem="camera_0",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(registrar),
            executor.submit(registrar),
        ]

        resultados = [
            future.result()
            for future in futures
        ]

    registrados = [
        resultado
        for resultado in resultados
        if resultado.registered
    ]

    historico = backend.historico_pessoa(
        pessoa_id=pessoa.id,
        limite=10,
    )

    assert len(registrados) == 1
    assert len(historico) == 1

    backend.fechar()
