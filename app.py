"""Application wiring for the in-process runner (sqlite-backed)."""
from typing import Optional

import models


def init_db(db_path: Optional[str] = None):
    path = db_path or "./db.sqlite"
    conn = models.init_db(path)
    return conn


def get_session():
    return models.make_session()
