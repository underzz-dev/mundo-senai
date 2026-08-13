# FacePoint — API do Backend

Este arquivo define o contrato oficial entre o backend e os outros módulos do FacePoint.

## Regra principal

Os outros integrantes devem importar apenas:

    from backend import FacePointBackend

Não acessar diretamente:

    backend._db
    backend._person_repo
    backend._attendance_repo
    backend._attendance_service
    backend._export_service

Não executar SQL diretamente.

---

## Inicialização

    from backend import FacePointBackend

    backend = FacePointBackend()

Ou:

    with FacePointBackend() as backend:
        ...

---

## Pessoas

### cadastrar_pessoa

    pessoa = backend.cadastrar_pessoa(
        nome="Ana Silva",
        matricula="MAT001",
    )

Retorna: Person

Possíveis erros:
- ValidationError
- DuplicateIdentifierError

---

### obter_pessoa

    pessoa = backend.obter_pessoa(1)

Retorna:

    Person | None

---

### listar_pessoas

Somente ativas:

    pessoas = backend.listar_pessoas()

Ativas e inativas:

    pessoas = backend.listar_pessoas(
        incluir_inativas=True
    )

Retorna:

    list[Person]

---

### atualizar_pessoa

Somente nome:

    backend.atualizar_pessoa(
        pessoa_id=1,
        nome="Ana Beatriz",
    )

Nome e matrícula:

    backend.atualizar_pessoa(
        pessoa_id=1,
        nome="Ana Beatriz",
        matricula="MAT002",
    )

Se a matrícula for omitida, a matrícula atual é preservada.

Retorna:

    True  -> atualizado
    False -> pessoa inexistente

---

### desativar_pessoa

    backend.desativar_pessoa(1)

A pessoa continua no banco, mas fica inativa.

---

### reativar_pessoa

    backend.reativar_pessoa(1)

---

## Registro de presença

Método principal usado pela Pessoa 1, responsável pelo reconhecimento facial:

    resultado = backend.registrar_presenca(
        pessoa_id=1,
        distancia=42.5,
        origem="camera_0",
    )

A Pessoa 1 deve fornecer:

    pessoa_id
    distancia
    origem

Usar "distancia".

Não usar:

    confidence
    confianca

O retorno é AttendanceResult.

Campos principais:

    resultado.success
    resultado.registered
    resultado.message
    resultado.person
    resultado.record_type
    resultado.timestamp
    resultado.distance
    resultado.cooldown_remaining_seconds

O backend controla:
- cooldown
- entrada
- saída
- gravação no banco

A Pessoa 1 NÃO deve implementar essas regras.

---

## Histórico

### Histórico geral

    registros = backend.listar_historico(
        limite=50
    )

### Histórico de uma pessoa

    registros = backend.historico_pessoa(
        pessoa_id=1,
        limite=50,
    )

### Histórico por data

    registros = backend.historico_data(
        "2026-08-13"
    )

Formato:

    YYYY-MM-DD

### Histórico por período

    registros = backend.historico_periodo(
        inicio="2026-08-01",
        fim="2026-08-13",
    )

---

## Métricas

    dados = backend.metricas()

Retorno atual:

    {
        "total_pessoas": int,
        "registros_hoje": int
    }

---

## Exportação CSV

    arquivo = backend.exportar_historico()

Ou:

    arquivo = backend.exportar_historico(
        caminho="exports/relatorio.csv"
    )

Colunas:

    pessoa_id
    nome
    data
    hora
    tipo
    distancia
    origem

---

## Pessoa 1 — Reconhecimento facial

Fluxo:

    câmera
       ↓
    reconhecimento
       ↓
    pessoa_id + distancia + origem
       ↓
    FacePointBackend.registrar_presenca()
       ↓
    AttendanceResult

Não deve acessar SQLite, repositories ou services.

---

## Pessoa 3 — Interface

Pode utilizar:

    cadastrar_pessoa()
    obter_pessoa()
    listar_pessoas()
    atualizar_pessoa()
    desativar_pessoa()
    reativar_pessoa()

    listar_historico()
    historico_pessoa()
    historico_data()
    historico_periodo()

    metricas()
    exportar_historico()

Não deve acessar SQLite, repositories ou services diretamente.

---

## Arquitetura

Fluxo correto:

    Interface / Reconhecimento
              ↓
       FacePointBackend
              ↓
           Services
              ↓
        Repositories
              ↓
           SQLite

FacePointBackend é a fronteira oficial entre os módulos.

---

## Estado atual

O backend possui:

- cadastro
- consulta
- listagem
- atualização
- desativação
- reativação
- entrada/saída
- cooldown
- histórico
- filtros
- métricas
- CSV
- SQLite
- testes de concorrência

Suíte atual:

    129 testes automatizados passando
