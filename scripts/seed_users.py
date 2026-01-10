#!/usr/bin/env python3
"""
Seed script to create initial user accounts.

Usage:
    # Set environment variables for passwords
    export SEED_PASSWORD_GARRETT="your_password"
    export SEED_PASSWORD_ERIK="your_password"
    export SEED_PASSWORD_CHRISTIAN="your_password"
    export SEED_PASSWORD_HENRY="your_password"

    # Run the script
    python scripts/seed_users.py
"""
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import User
from app.auth.utils import get_password_hash


# User definitions
USERS = [
    {
        "full_name": "Garrett Garcia",
        "email": "garrett@triumphroofing.com",
        "role": "Sales",
        "password_env": "SEED_PASSWORD_GARRETT",
    },
    {
        "full_name": "Erik",
        "email": "erik@triumphroofing.com",
        "role": "Estimator",
        "password_env": "SEED_PASSWORD_ERIK",
    },
    {
        "full_name": "Christian",
        "email": "christian@triumphroofing.com",
        "role": "Admin",  # Project management gets Admin for full access
        "password_env": "SEED_PASSWORD_CHRISTIAN",
    },
    {
        "full_name": "Henry",
        "email": "henry@triumphroofing.com",
        "role": "Admin",  # Owner gets Admin
        "password_env": "SEED_PASSWORD_HENRY",
    },
]


def seed_users():
    """Create user accounts from environment variables."""
    db = SessionLocal()
    created = []
    skipped = []
    errors = []

    try:
        for user_def in USERS:
            email = user_def["email"]

            # Check if user already exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                skipped.append(f"{user_def['full_name']} ({email}) - already exists")
                continue

            # Get password from environment
            password = os.getenv(user_def["password_env"])
            if not password:
                errors.append(f"{user_def['full_name']} - missing {user_def['password_env']} env var")
                continue

            # Create user
            user = User(
                full_name=user_def["full_name"],
                email=email,
                role=user_def["role"],
                password_hash=get_password_hash(password),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(user)
            created.append(f"{user_def['full_name']} ({email}) - {user_def['role']}")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()

    # Print summary
    print("\n=== User Seed Summary ===\n")

    if created:
        print("Created:")
        for item in created:
            print(f"  + {item}")

    if skipped:
        print("\nSkipped (already exist):")
        for item in skipped:
            print(f"  - {item}")

    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"  ! {item}")

    print(f"\nTotal: {len(created)} created, {len(skipped)} skipped, {len(errors)} errors")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    seed_users()
