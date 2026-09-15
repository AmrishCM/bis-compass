"""
Standalone Seed Ingestion Script for BIS-Compass
Executes knowledge base seeding into PostgreSQL/SQLite with verified official BIS standards.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal, init_db
from app.db.seed_data import seed_database
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing database schema...")
    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
        logger.info("Seed ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Failed to ingest seed data: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
