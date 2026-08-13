# -*- coding: utf-8 -*-
"""Initialize database tables from SQLAlchemy ORM models."""

from pathlib import Path
import sys

from sqlalchemy import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.models.db_models import Base


def init_db() -> None:
    """Create all missing tables declared on the ORM metadata."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required to initialize database tables.")

    engine = create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
    )

    Base.metadata.create_all(bind=engine, checkfirst=True)

    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    print(f"Database initialization complete. ORM tables checked: {table_names}")


if __name__ == "__main__":
    init_db()
