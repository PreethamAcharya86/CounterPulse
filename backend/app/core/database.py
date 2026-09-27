import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.config import settings

def _is_testing_environment() -> bool:
    return (
        os.environ.get("TESTING") == "true"
        or os.environ.get("PYTEST_CURRENT_TEST") is not None
        or "pytest" in sys.modules
    )

def get_database_url() -> str:
    if _is_testing_environment():
        return os.environ.get("TEST_DATABASE_URL") or "sqlite:///:memory:"
    return settings.DATABASE_URL

_db_url = get_database_url()

# In SQLite, check_same_thread=False allows multiple threads (e.g. FastAPI async requests)
connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args, "echo": False}
if _db_url == "sqlite:///:memory:":
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_migrations(db_engine):
    """Ensure newly added columns exist in existing SQLite databases."""
    from sqlalchemy import inspect, text
    inspector = inspect(db_engine)
    table_names = inspector.get_table_names()
    with db_engine.connect() as conn:
        if "cases" in table_names:
            c_cols = [c["name"] for c in inspector.get_columns("cases")]
            if "scam_category" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN scam_category VARCHAR(100);"))
            if "severity_level" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN severity_level VARCHAR(30) DEFAULT 'medium';"))
            if "financial_loss" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN financial_loss FLOAT;"))
            if "currency" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN currency VARCHAR(10) DEFAULT 'INR';"))
            if "modus_operandi" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN modus_operandi TEXT;"))
            if "summary" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN summary TEXT;"))
            if "intelligence_json" not in c_cols:
                conn.execute(text("ALTER TABLE cases ADD COLUMN intelligence_json TEXT;"))

        if "reports" in table_names:
            columns = [c["name"] for c in inspector.get_columns("reports")]
            if "sent_at" not in columns:
                conn.execute(text("ALTER TABLE reports ADD COLUMN sent_at DATETIME;"))
            if "recipient_email" not in columns:
                conn.execute(text("ALTER TABLE reports ADD COLUMN recipient_email VARCHAR(255);"))
            if "error_message" not in columns:
                conn.execute(text("ALTER TABLE reports ADD COLUMN error_message TEXT;"))
            if "evidence_references_json" not in columns:
                conn.execute(text("ALTER TABLE reports ADD COLUMN evidence_references_json TEXT;"))
            if "updated_at" not in columns:
                conn.execute(text("ALTER TABLE reports ADD COLUMN updated_at DATETIME;"))
        conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
