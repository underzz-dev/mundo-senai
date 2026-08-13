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
        distancia=42.0,
    )

    assert entrada.registered is True
    assert entrada.record_type == "entrada"

    # Cooldown
    repetido = backend.registrar_presenca(
        pessoa_id=pessoa.id,
        distancia=43.0,
    )

    assert repetido.registered is False

    # Saída
    saida = backend.registrar_presenca(
        pessoa_id=pessoa.id,
        distancia=41.0,
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
            distancia=42.0
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
def test_nao_permite_distancia_invalida(
    tmp_path,
    valor
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "distancia_invalida.db"
    )

    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001"
    )

    with pytest.raises(
        ValidationError,
        match="distância"
    ):
        backend.registrar_presenca(
            pessoa_id=pessoa.id,
            distancia=valor
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
            distancia=42.0,
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


@pytest.mark.parametrize(
    "ignorar_cooldown",
    [
        None,
        1,
        0,
        "sim",
        [],
        {},
    ],
)
def test_nao_permite_ignorar_cooldown_invalido(
    tmp_path,
    ignorar_cooldown
):
    from exceptions import ValidationError

    backend = FacePointBackend(
        db_path=tmp_path / "cooldown_invalido.db"
    )

    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    with pytest.raises(
        ValidationError,
        match="cooldown"
    ):
        backend.registrar_presenca(
            pessoa_id=pessoa.id,
            distancia=42.0,
            ignorar_cooldown=ignorar_cooldown,
        )

    backend.fechar()


@pytest.mark.parametrize(
    "cooldown_seconds",
    [
        0,
        -1,
        "60",
        10.5,
        True,
    ],
)
def test_nao_permite_cooldown_invalido_no_backend(
    tmp_path,
    cooldown_seconds
):
    from exceptions import ValidationError

    with pytest.raises(
        ValidationError,
        match="cooldown"
    ):
        backend = FacePointBackend(
            db_path=tmp_path / "cooldown_config.db",
            cooldown_seconds=cooldown_seconds,
        )

        backend.fechar()


def test_registrar_presenca_usa_distancia_na_api_publica(
    tmp_path
):
    backend = FacePointBackend(
        db_path=tmp_path / "distancia_api.db"
    )

    pessoa = backend.cadastrar_pessoa(
        nome="Gustavo",
        matricula="MAT001",
    )

    resultado = backend.registrar_presenca(
        pessoa_id=pessoa.id,
        distancia=42.5,
        origem="camera_0",
    )

    assert resultado.registered is True
    assert resultado.distance == 42.5

    backend.fechar()


def test_obter_pessoa_existente(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "obter_existente.db")
    cadastrada = backend.cadastrar_pessoa(nome="Carlos Silva", matricula="MAT777")

    encontrada = backend.obter_pessoa(cadastrada.id)

    assert encontrada is not None
    assert encontrada.id == cadastrada.id
    assert encontrada.name == "Carlos Silva"
    assert encontrada.identifier == "MAT777"

    backend.fechar()


def test_obter_pessoa_inexistente(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "obter_inexistente.db")

    encontrada = backend.obter_pessoa(999)

    assert encontrada is None

    backend.fechar()


@pytest.mark.parametrize(
    "id_invalido",
    [0, -1, -50, "1", 1.5, True, False, None],
)
def test_obter_pessoa_id_invalido(tmp_path, id_invalido):
    from exceptions import ValidationError

    backend = FacePointBackend(db_path=tmp_path / "obter_invalido.db")

    with pytest.raises(ValidationError, match="ID da pessoa"):
        backend.obter_pessoa(id_invalido)

    backend.fechar()


def test_listar_pessoas_somente_ativas_e_incluindo_inativas(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "listar_inativas.db")

    p1 = backend.cadastrar_pessoa(nome="Ana", matricula="MAT001")
    p2 = backend.cadastrar_pessoa(nome="Bruno", matricula="MAT002")

    backend.desativar_pessoa(p2.id)

    # Teste 1: listar somente ativas (padrão / incluir_inativas=False)
    ativas_padrao = backend.listar_pessoas()
    ativas_explicit = backend.listar_pessoas(incluir_inativas=False)

    assert len(ativas_padrao) == 1
    assert ativas_padrao[0].id == p1.id
    assert len(ativas_explicit) == 1
    assert ativas_explicit[0].id == p1.id

    # Teste 2: listar incluindo inativas (incluir_inativas=True)
    todas = backend.listar_pessoas(incluir_inativas=True)

    assert len(todas) == 2
    ids = [p.id for p in todas]
    assert p1.id in ids
    assert p2.id in ids

    backend.fechar()


@pytest.mark.parametrize(
    "valor_invalido",
    ["sim", "nao", 1, 0, None, [], {}],
)
def test_listar_pessoas_incluir_inativas_invalido(tmp_path, valor_invalido):
    from exceptions import ValidationError

    backend = FacePointBackend(db_path=tmp_path / "listar_param_invalido.db")

    with pytest.raises(ValidationError, match="incluir_inativas"):
        backend.listar_pessoas(incluir_inativas=valor_invalido)

    backend.fechar()


def test_reativar_pessoa_fluxo_completo(tmp_path):
    import time

    backend = FacePointBackend(db_path=tmp_path / "reativar_fluxo.db")

    # 1. Cadastrar pessoa
    p = backend.cadastrar_pessoa(nome="Daniela", matricula="MAT900")
    id_pessoa = p.id

    # 2. Desativar
    sucesso_desativar = backend.desativar_pessoa(id_pessoa)
    assert sucesso_desativar is True

    # 3. Confirmar que saiu de listar_pessoas()
    ativas = backend.listar_pessoas()
    assert not any(item.id == id_pessoa for item in ativas)

    # 4. Confirmar que aparece em listar_pessoas(incluir_inativas=True)
    todas = backend.listar_pessoas(incluir_inativas=True)
    inativa = next((item for item in todas if item.id == id_pessoa), None)
    assert inativa is not None
    assert inativa.active is False

    pessoa_desativada = backend.obter_pessoa(id_pessoa)
    assert pessoa_desativada is not None
    updated_at_desativada = pessoa_desativada.updated_at

    time.sleep(1.0)

    # 5. Reativar
    sucesso_reativar = backend.reativar_pessoa(id_pessoa)
    assert sucesso_reativar is True

    # 6. Confirmar que voltou para listar_pessoas()
    ativas_pos = backend.listar_pessoas()
    reativada = next((item for item in ativas_pos if item.id == id_pessoa), None)
    assert reativada is not None
    assert reativada.active is True

    # 7. Confirmar que atualizado_em muda ao reativar
    pessoa_reativada = backend.obter_pessoa(id_pessoa)
    assert pessoa_reativada is not None
    assert pessoa_reativada.updated_at != updated_at_desativada

    backend.fechar()


def test_reativar_pessoa_inexistente(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "reativar_inexistente.db")

    resultado = backend.reativar_pessoa(9999)
    assert resultado is False

    backend.fechar()


@pytest.mark.parametrize(
    "id_invalido",
    [0, -1, -100, "1", 2.5, True, False, None],
)
def test_reativar_pessoa_id_invalido(tmp_path, id_invalido):
    from exceptions import ValidationError

    backend = FacePointBackend(db_path=tmp_path / "reativar_invalido.db")

    with pytest.raises(ValidationError, match="ID da pessoa"):
        backend.reativar_pessoa(id_invalido)

    backend.fechar()


def test_atualizar_somente_nome(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "atualizar_nome.db")
    p = backend.cadastrar_pessoa(nome="Carlos Silva", matricula="MAT100")

    sucesso = backend.atualizar_pessoa(pessoa_id=p.id, nome="Carlos Eduardo Silva")
    assert sucesso is True

    atualizada = backend.obter_pessoa(p.id)
    assert atualizada.name == "Carlos Eduardo Silva"
    assert atualizada.identifier == "MAT100"

    backend.fechar()


def test_atualizar_nome_e_matricula_e_normalizacao(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "atualizar_nome_matricula.db")
    p = backend.cadastrar_pessoa(nome="Ana", matricula="MAT001")

    sucesso = backend.atualizar_pessoa(
        pessoa_id=p.id,
        nome="  Ana   Beatriz  ",
        matricula="  mat002  ",
    )
    assert sucesso is True

    atualizada = backend.obter_pessoa(p.id)
    assert atualizada.name == "Ana Beatriz"
    assert atualizada.identifier == "MAT002"

    backend.fechar()


def test_atualizar_manter_propria_matricula(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "manter_propria_matricula.db")
    p = backend.cadastrar_pessoa(nome="Gustavo", matricula="MAT001")

    # Atualizar nome mantendo exatamente a mesma matrícula ou alterando case ("mat001")
    sucesso = backend.atualizar_pessoa(
        pessoa_id=p.id,
        nome="Gustavo Franco",
        matricula="mat001",
    )
    assert sucesso is True

    atualizada = backend.obter_pessoa(p.id)
    assert atualizada.name == "Gustavo Franco"
    assert atualizada.identifier == "MAT001"

    backend.fechar()


def test_atualizar_matricula_duplicada_outra_pessoa(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "matricula_duplicada.db")
    p1 = backend.cadastrar_pessoa(nome="Pessoa Um", matricula="MAT001")
    p2 = backend.cadastrar_pessoa(nome="Pessoa Dois", matricula="MAT002")

    # Tentar atualizar p2 para usar a matrícula de p1 (case-insensitive)
    with pytest.raises(DuplicateIdentifierError, match="já está cadastrada"):
        backend.atualizar_pessoa(
            pessoa_id=p2.id,
            nome="Pessoa Dois Alterada",
            matricula="mat001",
        )

    # Confirmar que os dados de p2 não foram alterados
    p2_banco = backend.obter_pessoa(p2.id)
    assert p2_banco.name == "Pessoa Dois"
    assert p2_banco.identifier == "MAT002"

    backend.fechar()


def test_atualizar_pessoa_inexistente(tmp_path):
    backend = FacePointBackend(db_path=tmp_path / "pessoa_inexistente.db")

    resultado = backend.atualizar_pessoa(
        pessoa_id=9999,
        nome="Pessoa Inexistente",
        matricula="MAT999",
    )
    assert resultado is False

    backend.fechar()


@pytest.mark.parametrize(
    "id_invalido",
    [0, -1, -50, "1", 2.5, True, False, None],
)
def test_atualizar_pessoa_id_invalido(tmp_path, id_invalido):
    from exceptions import ValidationError

    backend = FacePointBackend(db_path=tmp_path / "atualizar_id_invalido.db")

    with pytest.raises(ValidationError, match="ID da pessoa"):
        backend.atualizar_pessoa(
            pessoa_id=id_invalido,
            nome="Nome Valido",
        )

    backend.fechar()


@pytest.mark.parametrize(
    "nome_invalido",
    ["", "   ", None, 123, True, False, []],
)
def test_atualizar_pessoa_nome_vazio(tmp_path, nome_invalido):
    from exceptions import ValidationError

    backend = FacePointBackend(db_path=tmp_path / "atualizar_nome_vazio.db")
    p = backend.cadastrar_pessoa(nome="Pedro", matricula="MAT500")

    with pytest.raises(ValidationError, match="nome da pessoa é obrigatório"):
        backend.atualizar_pessoa(
            pessoa_id=p.id,
            nome=nome_invalido,
        )

    backend.fechar()


def test_atualizar_pessoa_inativa_mantem_inativa(tmp_path):
    import time

    backend = FacePointBackend(db_path=tmp_path / "atualizar_inativa.db")
    p = backend.cadastrar_pessoa(nome="Inativo", matricula="MAT100")

    backend.desativar_pessoa(p.id)

    inativa_antes = backend.obter_pessoa(p.id)
    assert inativa_antes.active is False
    created_at_original = inativa_antes.created_at
    updated_at_antes = inativa_antes.updated_at

    time.sleep(1.0)

    # Atualizar dados da pessoa inativa
    sucesso = backend.atualizar_pessoa(
        pessoa_id=p.id,
        nome="Inativo Nome Alterado",
        matricula="MAT100_ALT",
    )
    assert sucesso is True

    # Verificar que a pessoa continua inativa
    inativa_depois = backend.obter_pessoa(p.id)
    assert inativa_depois.active is False
    assert inativa_depois.name == "Inativo Nome Alterado"
    assert inativa_depois.identifier == "MAT100_ALT"

    # Verificar timestamps: criado_em não muda, atualizado_em muda
    assert inativa_depois.created_at == created_at_original
    assert inativa_depois.updated_at != updated_at_antes

    # Garantir que NÃO voltou para a lista de ativas
    ativas = backend.listar_pessoas(incluir_inativas=False)
    assert not any(item.id == p.id for item in ativas)

    backend.fechar()


def test_atualizar_pessoa_persistencia_sqlite(tmp_path):
    db_file = tmp_path / "persistencia.db"

    # 1. Abre backend, cadastra e atualiza
    backend1 = FacePointBackend(db_path=db_file)
    p = backend1.cadastrar_pessoa(nome="Original", matricula="MAT001")
    backend1.atualizar_pessoa(pessoa_id=p.id, nome="Persistido", matricula="MAT001_PER")
    backend1.fechar()

    # 2. Reabre o SQLite em nova instância do backend
    backend2 = FacePointBackend(db_path=db_file)
    reaberta = backend2.obter_pessoa(p.id)

    assert reaberta is not None
    assert reaberta.name == "Persistido"
    assert reaberta.identifier == "MAT001_PER"

    backend2.fechar()
