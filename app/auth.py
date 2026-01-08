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

# Demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session serializer
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production-min-32-chars")
SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "480"))
serializer = URLSafeTimedSerializer(SECRET_KEY)


def get_demo_user() -> User:
    """Return a demo user object for DEMO_MODE."""
    user = User()
    user.id = 1
    user.email = "demo@triumphcrm.com"
    user.full_name = "Demo User"
    user.role = "Admin"
    user.is_active = True
    return user


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


async def get_current_user(
    request: Request,
    db: Optional[Session] = Depends(get_db)
) -> Optional[User]:
    """Get current user from session."""
    if DEMO_MODE or db is None:
        return get_demo_user()

    user_id = get_session_user_id(request)
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user


async def require_auth(
    request: Request,
    db: Optional[Session] = Depends(get_db)
) -> User:
    """Require authenticated user, redirect to login if not."""
    if DEMO_MODE or db is None:
        return get_demo_user()

    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login?next=" + str(request.url.path)}
        )
    return user


def require_role(*roles):
    """Decorator to require specific roles."""
    async def dependency(
        request: Request,
        db: Optional[Session] = Depends(get_db)
    ) -> User:
        if DEMO_MODE or db is None:
            user = get_demo_user()
        else:
            user = await require_auth(request, db)

        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )
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
    if DEMO_MODE or db is None:
        return get_demo_user()

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
