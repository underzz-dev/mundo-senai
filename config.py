import os
from pathlib import Path

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent

# Dados do backend
DATA_DIR = BASE_DIR / "data"
DB_NAME = os.getenv("FACEPOINT_DB_NAME", "facepoint.db")
DB_PATH = DATA_DIR / DB_NAME

# Modelo de Reconhecimento Facial
MODEL_NAME = "facepoint_model.yml"
MODEL_PATH = BASE_DIR / MODEL_NAME

# Configurações de Regra de Ponto
COOLDOWN_SECONDS = int(os.getenv("FACEPOINT_COOLDOWN", "60"))
MATCH_THRESHOLD = float(os.getenv("FACEPOINT_MATCH_THRESHOLD", "70.0"))
STABLE_FRAMES = int(os.getenv("FACEPOINT_STABLE_FRAMES", "8"))

# Configurações de Câmera e Captura
CAMERA_INDEX = int(os.getenv("FACEPOINT_CAMERA_INDEX", "0"))
FRAME_INTERVAL_MS = 33
FACE_SIZE = (160, 160)
ENROLL_SAMPLES = 30
ENROLL_EVERY_N_FRAMES = 3

# Exportação
EXPORTS_DIR = BASE_DIR / "exports"
