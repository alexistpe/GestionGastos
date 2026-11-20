import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from database import db  # noqa: E402


@pytest.fixture
def db_path(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    return ruta
