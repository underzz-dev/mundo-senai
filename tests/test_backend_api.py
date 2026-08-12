import pytest
from backend import FacePointBackend
from exceptions import DuplicateIdentifierError


def test_api_publica_backend(tmp_path):
    banco = tmp_path / "facepoint_api.db"

    backend = FacePointBackend(
        db_path=banco,
        cooldown_seconds=60,
    )

    # Cadastro
    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    assert pessoa.id is not None

    # Listagem
    pessoas = backend.listar_pessoas()

    assert len(pessoas) == 1
    assert pessoas[0].name == "Gustavo"

    # Entrada
    entrada = backend.registrar_presenca(
        pessoa_id=pessoa.id,
        confianca=42.0,
    )

    assert entrada.registered is True
    assert entrada.record_type == "entrada"

    # Cooldown
    repetido = backend.registrar_presenca(
        pessoa_id=pessoa.id,
        confianca=43.0,
    )

    assert repetido.registered is False

    # Saída
    saida = backend.registrar_presenca(
        pessoa_id=pessoa.id,
        confianca=41.0,
        ignorar_cooldown=True,
    )

    assert saida.registered is True
    assert saida.record_type == "saida"

    # Histórico
    historico = backend.listar_historico()

    assert len(historico) == 2

    # Exportação
    csv_path = tmp_path / "historico.csv"

    resultado = backend.exportar_historico(
        csv_path
    )

    assert resultado.exists()

    # Métricas
    metricas = backend.metricas()

    assert metricas["total_pessoas"] == 1
    assert metricas["registros_hoje"] == 2

    backend.fechar()


def test_nao_permite_matricula_duplicada(tmp_path):
    banco = tmp_path / "duplicada.db"

    backend = FacePointBackend(
        db_path=banco
    )

    primeira = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    assert primeira.id is not None

    with pytest.raises(
        DuplicateIdentifierError
    ):
        backend.cadastrar_pessoa(
            nome="Ana",
            matricula="MAT001",
        )

    backend.fechar()



def test_matricula_duplicada_case_insensitive(tmp_path):
    banco = tmp_path / "duplicada_case.db"

    backend = FacePointBackend(
        db_path=banco
    )

    backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    with pytest.raises(
        DuplicateIdentifierError
    ):
        backend.cadastrar_pessoa(
            nome="Ana",
            matricula="mat001",
        )

    backend.fechar()


def test_nao_permite_nome_vazio(tmp_path):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "nome_vazio.db"
    )

    with pytest.raises(
        ValidationError,
        match="nome"
    ):
        backend.cadastrar_pessoa(
            nome="   ",
            matricula="MAT999"
        )

    assert backend.listar_pessoas() == []

    backend.fechar()


def test_nao_permite_pessoa_id_invalido(tmp_path):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "id_invalido.db"
    )

    with pytest.raises(
        ValidationError,
        match="ID"
    ):
        backend.registrar_presenca(
            pessoa_id=0,
            confianca=42.0
        )

    backend.fechar()


@pytest.mark.parametrize(
    "valor",
    [
        None,
        "42",
        True,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_nao_permite_confianca_invalida(
    tmp_path,
    valor
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "confianca_invalida.db"
    )

    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001"
    )

    with pytest.raises(
        ValidationError,
        match="confiança"
    ):
        backend.registrar_presenca(
            pessoa_id=pessoa.id,
            confianca=valor
        )

    backend.fechar()


@pytest.mark.parametrize(
    "origem",
    [
        None,
        "",
        "   ",
        123,
        True,
    ],
)
def test_nao_permite_origem_invalida(
    tmp_path,
    origem
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "origem_invalida.db"
    )

    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001"
    )

    with pytest.raises(
        ValidationError,
        match="origem"
    ):
        backend.registrar_presenca(
            pessoa_id=pessoa.id,
            confianca=42.0,
            origem=origem
        )

    backend.fechar()


@pytest.mark.parametrize(
    "limite",
    [
        None,
        0,
        -1,
        "50",
        10.5,
        True,
    ],
)
def test_nao_permite_limite_invalido_no_historico(
    tmp_path,
    limite
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "limite_invalido.db"
    )

    with pytest.raises(
        ValidationError,
        match="limite"
    ):
        backend.listar_historico(
            limite=limite
        )

    backend.fechar()


@pytest.mark.parametrize(
    "data",
    [
        None,
        "",
        "12/08/2026",
        "2026-13-01",
        "2026-02-30",
    ],
)
def test_nao_permite_data_invalida_no_historico(
    tmp_path,
    data
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "data_invalida.db"
    )

    with pytest.raises(
        ValidationError,
        match="data"
    ):
        backend.historico_data(
            data=data
        )

    backend.fechar()


@pytest.mark.parametrize(
    "inicio,fim",
    [
        (None, "2026-08-12"),
        ("2026-08-10", None),
        ("12/08/2026", "2026-08-12"),
        ("2026-08-10", "31/08/2026"),
        ("2026-02-30", "2026-03-01"),
        ("2026-09-01", "2026-08-01"),
    ],
)
def test_nao_permite_periodo_invalido(
    tmp_path,
    inicio,
    fim
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "periodo_invalido.db"
    )

    with pytest.raises(
        ValidationError
    ):
        backend.historico_periodo(
            inicio=inicio,
            fim=fim,
        )

    backend.fechar()


@pytest.mark.parametrize(
    "pessoa_id",
    [
        None,
        0,
        -1,
        "1",
        1.5,
        True,
    ],
)
def test_nao_permite_id_invalido_ao_desativar(
    tmp_path,
    pessoa_id
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "id_desativar.db"
    )

    with pytest.raises(
        ValidationError,
        match="ID"
    ):
        backend.desativar_pessoa(
            pessoa_id
        )

    backend.fechar()


@pytest.mark.parametrize(
    "pessoa_id",
    [
        None,
        0,
        -1,
        "1",
        1.5,
        True,
    ],
)
def test_nao_permite_id_invalido_no_historico_pessoa(
    tmp_path,
    pessoa_id
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "id_historico.db"
    )

    with pytest.raises(
        ValidationError,
        match="ID"
    ):
        backend.historico_pessoa(
            pessoa_id=pessoa_id
        )

    backend.fechar()
