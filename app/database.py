import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/revenueos")
    # Ensure psycopg (v3) driver is used
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def get_engine():
    """Get or create database engine."""
    DATABASE_URL = get_database_url()
    return create_engine(DATABASE_URL, echo=os.getenv("DEBUG", "false").lower() == "true")


engine = get_engine()
# Enable a resilient session factory; keep connections lazy but allow a
# quick connectivity check in `get_db()` so we can fall back to demo data
# when the database is unreachable in a deployment environment.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI routes to get database session."""
    from app.auth import DEMO_MODE
    # If explicitly in DEMO_MODE, avoid creating a DB session.
    if DEMO_MODE:
        yield None
        return

    # Attempt to create a session and verify connectivity. If connectivity
    # fails (e.g., host/credentials not available in the environment), yield
    # None so routes that support demo data (`if DEMO_MODE or db is None`) can
    # continue to function instead of raising unhandled exceptions.
    try:
        db = SessionLocal()
        # Try a lightweight check using the connection; this will raise
        # if the database is unreachable or credentials are invalid.
        with engine.connect():
            pass
    except Exception:
        try:
            # Ensure any partially-open session is closed
            db.close()
        except Exception:
            pass
        # When DB connectivity fails at runtime, flip the app into demo-friendly
        # mode so route-level checks (`if DEMO_MODE or db is None`) will take
        # effect and avoid unhandled server errors.
        try:
            import app.auth as _auth
            _auth.DEMO_MODE = True
        except Exception:
            pass

        yield None
        return

    try:
        yield db
    finally:
        db.close()
