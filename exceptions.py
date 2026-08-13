class FacePointError(Exception):
    """Erro base do backend FacePoint."""


class DuplicateIdentifierError(FacePointError):
    """Matrícula/identificador já cadastrado."""



class DatabaseMigrationError(FacePointError):
    """Banco antigo possui dados incompatíveis com a migração."""



class ValidationError(FacePointError):
    """Dados recebidos pelo backend são inválidos."""
