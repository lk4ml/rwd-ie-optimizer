"""
Database connection utilities.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
import os


def get_db_path() -> Path:
    """Get the path to the SQLite database."""
    db_path_env = os.getenv("DATABASE_PATH", "data/rwd_claims.db")

    # If relative path, make it relative to project root
    if not Path(db_path_env).is_absolute():
        project_root = Path(__file__).parent.parent.parent
        return project_root / db_path_env
    else:
        return Path(db_path_env)


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patients")
    """
    db_path = get_db_path()

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run 'python scripts/create_database.py' first."
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name

    try:
        yield conn
    finally:
        conn.close()
