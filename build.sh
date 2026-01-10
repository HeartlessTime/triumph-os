#!/usr/bin/env bash
set -e

pip install -r requirements.txt

python3 -m alembic upgrade head
