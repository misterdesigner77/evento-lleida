import sqlite3
from pathlib import Path
import config as c

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def db():
    con = sqlite3.connect(c.DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def open_db():
    c.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = db()
    try:
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        print("Banco criado!")
    finally:
        con.close()


if __name__ == "__main__":
    open_db()