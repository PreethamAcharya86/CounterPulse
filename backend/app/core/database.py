from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

# In SQLite, check_same_thread=False allows multiple threads (e.g. FastAPI async requests)
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

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
