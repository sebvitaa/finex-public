import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db.init_db import init_db


if __name__ == "__main__":
    init_db()
    print("SQLite local inicializado y categorias base sembradas.")
