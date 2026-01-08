import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from functools import wraps

from app.database import get_db
from app.models.user import User

# Password hashing
# Use a compatible hashing scheme for SQLite/dev when bcrypt may be unavailable
from app.database import DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    # pbkdf2_sha256 is widely available and avoids compiled bcrypt issues in dev
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
else:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session serializer
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production-min-32-chars")
SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "480"))
serializer = URLSafeTimedSerializer(SECRET_KEY)


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int) -> str:
    """Create a session token for a user."""
    data = {
        "user_id": user_id,
        "created": datetime.utcnow().isoformat()
    }
    return serializer.dumps(data)


def decode_session_token(token: str) -> Optional[dict]:
    """Decode and validate a session token."""
    try:
        data = serializer.loads(token, max_age=SESSION_EXPIRE_MINUTES * 60)
        return data
    except (BadSignature, SignatureExpired):
        return None


def get_session_user_id(request: Request) -> Optional[int]:
    """Get user ID from session cookie."""
    token = request.cookies.get("session")
    if not token:
        return None
    
    data = decode_session_token(token)
    if not data:
        return None
    
    return data.get("user_id")


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Return a current demo user. Authentication is disabled in demo mode.

    This will return the first active user in the DB if present, or create
    a lightweight demo user in-memory when none exist.
    """
    # Prefer any existing active user (seed creates users at startup)
    user = db.query(User).filter(User.is_active == True).first()
    if user:
        return user

    # Fallback: create an ephemeral demo user (not persisted beyond runtime)
    demo = User(email="demo@triumphos.local", full_name="Demo User", role="Admin", is_active=True)
    # Do not set password_hash; this user is not authenticated via login
    return demo


async def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Return a user without performing authentication checks (demo mode)."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No demo user available")
    return user


def require_role(*roles):
    """Decorator to require specific roles."""
    async def dependency(request: Request, db: Session = Depends(get_db)) -> User:
        # In demo mode, allow access and return a demo user
        user = await require_auth(request, db)
        return user
    return Depends(dependency)


def require_admin():
    """Require admin role."""
    return require_role('Admin')


def require_sales_or_admin():
    """Require sales or admin role."""
    return require_role('Admin', 'Sales')


def require_estimator_or_admin():
    """Require estimator or admin role."""
    return require_role('Admin', 'Estimator')


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def set_session_cookie(response, user_id: int):
    """Set session cookie on response."""
    token = create_session_token(user_id)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        max_age=SESSION_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


def clear_session_cookie(response):
    """Clear session cookie on response."""
    response.delete_cookie("session")
    return response
