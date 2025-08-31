from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, event, inspect
from models import WordDict, QuizAgg, PhraseDict, Base
import pandas as pd
import uuid
from datetime import datetime

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

