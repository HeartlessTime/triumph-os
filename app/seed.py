#!/usr/bin/env python3
"""
Database Seeding for Triumph OS

Usage:
    python -m app.seed              # Create CEO user if no users exist
    SEED_DEMO=true python -m app.seed   # Also create demo users if missing

Behavior:
    - If NO users exist: Creates one CEO/Admin user
    - If users exist: Does nothing (unless SEED_DEMO=true)
    - SEED_DEMO=true: Creates demo Sales/Estimator users if they don't exist
    - Safe to run multiple times (idempotent)

This script does NOT:
    - Auto-run on application startup
    - Modify existing users
    - Change the database schema
"""

import os
import sys

# Ensure we can import app modules
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import User
from app.auth.utils import get_password_hash


# =============================================================================
# USER CONFIGURATION
# =============================================================================

# CEO user - created when database has no users
CEO_USER = {
    "email": "ggarcia@triumph-cs.com",
    "full_name": "Garrett Garcia",
    "role": "Admin",
    "password": "triumph2024!",  # Change in production
}

# Demo users - only created when SEED_DEMO=true
DEMO_USERS = [
    {
        "email": "sales@triumph-cs.com",
        "full_name": "Sarah Sales",
        "role": "Sales",
        "password": "demo123!",
    },
    {
        "email": "estimator@triumph-cs.com",
        "full_name": "Eric Estimator",
        "role": "Estimator",
        "password": "demo123!",
    },
]


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================


def user_exists(db, email: str) -> bool:
    """Check if a user with the given email exists."""
    return db.query(User).filter(User.email == email).first() is not None


def create_user(db, user_data: dict) -> User:
    """Create a user with proper password hashing."""
    user = User(
        email=user_data["email"],
        full_name=user_data["full_name"],
        role=user_data["role"],
        password_hash=get_password_hash(user_data["password"]),
        is_active=True,
    )
    db.add(user)
    return user


def seed_ceo_user(db) -> bool:
    """
    Create CEO user if no users exist in the database.
    Returns True if user was created, False if skipped.
    """
    user_count = db.query(User).count()

    if user_count > 0:
        print(f"  [SKIP] {user_count} user(s) already exist - CEO user not needed")
        return False

    print(f"  [CREATE] CEO user: {CEO_USER['email']}")
    create_user(db, CEO_USER)
    return True


def seed_demo_users(db) -> int:
    """
    Create demo users if they don't exist.
    Returns count of users created.
    """
    created_count = 0

    for user_data in DEMO_USERS:
        if user_exists(db, user_data["email"]):
            print(f"  [SKIP] Demo user exists: {user_data['email']}")
        else:
            print(f"  [CREATE] Demo user: {user_data['email']} ({user_data['role']})")
            create_user(db, user_data)
            created_count += 1

    return created_count


def main():
    """Main seeding entry point."""
    print("=" * 60)
    print("TRIUMPH OS - DATABASE SEEDING")
    print("=" * 60)

    seed_demo = os.getenv("SEED_DEMO", "false").lower() == "true"

    if seed_demo:
        print("Mode: SEED_DEMO=true (will create demo users if missing)")
    else:
        print("Mode: Standard (CEO user only if no users exist)")

    print()

    db = SessionLocal()
    try:
        # Phase 1: CEO user (only if no users exist)
        print("Phase 1: CEO User")
        ceo_created = seed_ceo_user(db)

        # Phase 2: Demo users (only if SEED_DEMO=true)
        demo_created = 0
        if seed_demo:
            print("\nPhase 2: Demo Users")
            demo_created = seed_demo_users(db)
        else:
            print("\nPhase 2: Demo Users [SKIPPED - set SEED_DEMO=true to enable]")

        # Commit all changes
        db.commit()

        # Summary
        print("\n" + "=" * 60)
        print("SEEDING COMPLETE")
        print("=" * 60)
        total_created = (1 if ceo_created else 0) + demo_created
        if total_created > 0:
            print(f"Created {total_created} user(s)")
        else:
            print("No changes made (all users already exist)")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
