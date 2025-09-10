from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, event, inspect, text
from models import WordDict, QuizAgg, PhraseDict, QuizLog, Base
import pandas as pd
import uuid
from datetime import datetime
from pathlib import Path

engine = create_engine("sqlite:///mydata.db", future=True)

# Turn on FK enforcement for SQLite connections on this engine
if engine.url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        # Works for pysqlite
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db() -> None:
    """Create any missing tables. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)

def ensure_views_from_files(dir_rel: str = "sql/views") -> None:
    """
    DROP + CREATE each .sql file as a view.
    Each file should contain the SELECT body (or a full CREATE VIEW if you prefer).
    Idempotent and safe to call on startup.
    """
    root = Path(__file__).parent / dir_rel
    if not root.exists():
        return  # nothing to do in dev/first run

    with engine.begin() as conn:
        for path in sorted(root.glob("*.sql")):
            name = path.stem  # view name = filename without .sql
            sql_body = path.read_text(encoding="utf-8").strip().rstrip(";")

            # SQLite doesn't support CREATE OR REPLACE VIEW → use DROP first
            conn.execute(text(f"DROP VIEW IF EXISTS {name}"))
            conn.execute(text(f"CREATE VIEW {name} AS {sql_body}"))