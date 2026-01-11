"""
Authentication utilities for session-based auth.
"""

from typing import Optional

from fastapi import Request, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt has a 72-byte limit on passwords
BCRYPT_MAX_BYTES = 72


def _safe_password(password: str) -> bytes:
    """
    Encode password and truncate to bcrypt's 72-byte limit if needed.
    This ensures compatibility across different bcrypt library versions.
    """
    password_bytes = password.encode("utf-8")
    return password_bytes[:BCRYPT_MAX_BYTES]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(_safe_password(plain_password), hashed_password)
    except Exception:
        # Handle malformed hashes or other bcrypt errors gracefully
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(_safe_password(password))


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user from session if logged in.
    Returns None if not authenticated.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Get the current user from session.
    Raises HTTPException if not authenticated.
    """
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency that returns the user or None.
    Used when middleware handles redirects.
    """
    return get_current_user_optional(request, db)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.
    Returns the user if authentication succeeds, None otherwise.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
