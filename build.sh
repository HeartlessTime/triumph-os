#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Fix alembic_version table if it exists with wrong column size
python3 -c "
import os
from sqlalchemy import create_engine, text
from app.database import get_database_url

try:
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        # Check if table exists and alter if needed
        result = conn.execute(text(
            \"\"\"
            SELECT column_name, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alembic_version' AND column_name = 'version_num'
            \"\"\"
        ))
        row = result.fetchone()
        if row and row[1] and row[1] < 128:
            print('Altering alembic_version.version_num to VARCHAR(128)...')
            conn.execute(text('ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)'))
            conn.commit()
            print('Done!')
except Exception as e:
    print(f'Note: {e}')
    pass
"

# Run database migrations
alembic upgrade head
