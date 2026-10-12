import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # variáveis de ambiente reais têm prioridade sobre o .env

DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "topazio.db"))

ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

TAMANHO = 4
