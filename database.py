from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, event, inspect, text
from models import WordDict, QuizAgg, PhraseDict, QuizLog, Base, WordComparison, APILatencyLog
import hashlib
import pandas as pd
import uuid
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()


engine = create_engine(f"sqlite:///{os.getenv('DB_PATH')}", future=True)

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
    backfill_pair_ids()
    migrate_quiz_log_columns()


def migrate_quiz_log_columns() -> None:
    """
    Add is_top_pinyin_error and is_top_meaning_error columns to QuizLog if missing.
    Safe to call on every startup — no-op once columns exist.
    """
    with engine.begin() as conn:
        existing = [row[1] for row in conn.execute(text("PRAGMA table_info(QuizLog)"))]
        if 'is_top_pinyin_error' not in existing:
            conn.execute(text("ALTER TABLE QuizLog ADD COLUMN is_top_pinyin_error INTEGER"))
        if 'is_top_meaning_error' not in existing:
            conn.execute(text("ALTER TABLE QuizLog ADD COLUMN is_top_meaning_error INTEGER"))


def backfill_pair_ids() -> None:
    """
    Ensure the pair_id column exists in WordComparison and populate any NULL values.
    Safe to call on every startup — is a no-op once all rows are backfilled.
    """
    with engine.begin() as conn:
        # Add column if it doesn't exist yet (SQLite supports ADD COLUMN)
        existing = [row[1] for row in conn.execute(text("PRAGMA table_info(WordComparison)"))]
        if 'pair_id' not in existing:
            conn.execute(text("ALTER TABLE WordComparison ADD COLUMN pair_id TEXT"))

        # Backfill rows that still have NULL pair_id
        rows = conn.execute(
            text("SELECT id, word1, word2 FROM WordComparison WHERE pair_id IS NULL")
        ).fetchall()
        for row_id, word1, word2 in rows:
            raw = f"{(word1 or '').strip()}|{(word2 or '').strip()}"
            pair_id = "WP" + hashlib.sha256(raw.encode()).hexdigest()[:12]
            conn.execute(
                text("UPDATE WordComparison SET pair_id = :pid WHERE id = :id"),
                {"pid": pair_id, "id": row_id},
            )

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