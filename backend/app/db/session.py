from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Base directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
FALLBACK_SQLITE_PATH = BACKEND_DIR / "bis_compass.db"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{FALLBACK_SQLITE_PATH.as_posix()}"

engine = None
SessionLocal = None
is_sqlite = False

def create_db_engine():
    global engine, SessionLocal, is_sqlite, SQLALCHEMY_DATABASE_URL
    target_url = SQLALCHEMY_DATABASE_URL

    # If postgresql is configured, test if it's reachable
    if target_url.startswith("postgresql"):
        try:
            test_engine = create_engine(
                target_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3}
            )
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL database successfully.")
            engine = test_engine
            is_sqlite = False
        except Exception as e:
            logger.warning(
                f"PostgreSQL connection to {target_url} failed ({e}). "
                f"Falling back to local SQLite database at {FALLBACK_SQLITE_PATH}."
            )
            target_url = f"sqlite:///{FALLBACK_SQLITE_PATH.as_posix()}"
            engine = create_engine(
                target_url,
                connect_args={"check_same_thread": False}
            )
            is_sqlite = True
    else:
        is_sqlite = True
        engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False} if "sqlite" in target_url else {}
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine

create_db_engine()

# Create base class for models
Base = declarative_base()

def get_db():
    """Dependency to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and ensure schema is up to date."""
    from app.models import standard  # Ensure models are imported
    from sqlalchemy import inspect

    Base.metadata.create_all(bind=engine)

    # Auto-migrate missing columns for SQLite/Postgres fallback
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if "standards" in existing_tables:
            cols = {c["name"] for c in inspector.get_columns("standards")}
            with engine.connect() as conn:
                if "relationship_type" not in cols:
                    conn.execute(text("ALTER TABLE standards ADD COLUMN relationship_type VARCHAR(50) DEFAULT 'PRIMARY_PRODUCT_STANDARD'"))
                if "parent_standard_id" not in cols:
                    conn.execute(text("ALTER TABLE standards ADD COLUMN parent_standard_id INTEGER"))
                if "authority_tier" not in cols:
                    conn.execute(text("ALTER TABLE standards ADD COLUMN authority_tier INTEGER DEFAULT 1"))
                if "is_qco_mandatory" not in cols:
                    conn.execute(text("ALTER TABLE standards ADD COLUMN is_qco_mandatory BOOLEAN DEFAULT 0"))
                conn.commit()

        if "laboratories" in existing_tables:
            lab_cols = {c["name"] for c in inspector.get_columns("laboratories")}
            with engine.connect() as conn:
                if "source_url" not in lab_cols:
                    conn.execute(text("ALTER TABLE laboratories ADD COLUMN source_url VARCHAR(1000)"))
                if "verified_date" not in lab_cols:
                    conn.execute(text("ALTER TABLE laboratories ADD COLUMN verified_date DATETIME"))
                conn.commit()
    except Exception as e:
        logger.warning(f"Schema auto-migration notice: {e}")

    logger.info("Database tables verified/created.")