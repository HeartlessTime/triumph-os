import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()

# Demo-mode default: in-memory SQLite (no persistence beyond runtime)
# This app has been converted to demo-only, so default to an in-memory DB.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")

# Use SQLite-specific connect args and a StaticPool so the in-memory DB
# stays live for the lifetime of the process across connections.
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    **engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(create_tables_for_sqlite: bool = True):
    """Initialize DB connection. For SQLite (dev) can auto-create tables.

    Raises a RuntimeError if the DB cannot be reached/initialized.
    """
    try:
        # Try a simple connection check
        with engine.connect() as conn:
            pass
    except Exception as e:
        raise RuntimeError(f"Unable to connect to database at '{DATABASE_URL}': {e}") from e

    # If using SQLite in dev, optionally create all tables automatically
    if create_tables_for_sqlite and DATABASE_URL.startswith("sqlite"):
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            raise RuntimeError(f"Failed creating SQLite tables: {e}") from e
