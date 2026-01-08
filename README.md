# Triumph OS

A production-ready internal web application that connects Sales and Estimating teams in one unified database.

## Features

- **Account & Contact Management**: Create and edit accounts and contacts
- **Opportunity Intake**: Create opportunities with bid dates, scope packages, and documents
- **Opportunity Command Center**: Single page showing everything about a deal
- **Estimating**: Create versioned estimates with line items, labor/materials, margins
- **Proposal Generator**: Generate PDF proposals from estimates
- **Follow-up Engine**: Automated follow-up date calculations based on stage and bid dates
- **Role-Based Access**: Sales, Estimator, and Admin roles

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy + Alembic migrations
- **Frontend**: Server-rendered Jinja2 templates
- **Auth**: Session-based login with role-based access control
- **File Storage**: Local `/uploads` directory for MVP
- **PDF Generation**: ReportLab

---

## Mac Installation

### Prerequisites

1. **Install Homebrew** (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. **Install Python 3.11+**:
```bash
brew install python@3.11
```

3. **Install PostgreSQL**:
```bash
brew install postgresql@15
```

4. **Start PostgreSQL**:
```bash
brew services start postgresql@15
```

### Setup

1. **Extract the zip and navigate to the project**:
```bash
unzip triumphos.zip
cd triumphos
```

2. **Create and activate virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Create the database**:
```bash
createdb triumphos
```

> **Note**: If you get a "role does not exist" error, first create your user:
> ```bash
> createuser -s $(whoami)
> ```

5. **Configure environment** (optional - defaults work for local dev):
```bash
cp .env.example .env
```

If your PostgreSQL uses a different user/password, edit `.env`:
```
DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/triumphos
```

6. **Run database migrations**:
```bash
alembic upgrade head
```

If you added the intake schema changes, run the new migration (already included):
```bash
alembic upgrade head
```

7. **Seed the database with sample data**:
```bash
python -m app.seed
```

8. **Start the server**:
```bash
uvicorn app.main:app --reload --port 8000
```

9. **Open the application**:
```
http://localhost:8000
```

---

## Default Login Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@triumphos.com | admin123 | Admin |
| sarah.sales@triumphos.com | sales123 | Sales |
| mike.estimator@triumphos.com | estimate123 | Estimator |

---

## Troubleshooting (Mac)

### PostgreSQL connection issues

Check PostgreSQL is running:
```bash
brew services list
```

Restart if needed:
```bash
brew services restart postgresql@15
```

### psycopg2 build errors

If `psycopg2-binary` fails to install:
```bash
brew install libpq
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
pip install psycopg2-binary
```

### Permission errors on uploads folder

```bash
mkdir -p uploads
chmod 755 uploads
```

### Port 8000 already in use

Use a different port:
```bash
uvicorn app.main:app --reload --port 8080
```

---

## Project Structure

```
triumphos/
├── alembic/                 # Database migrations
├── app/
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # FastAPI route handlers
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 templates
│   ├── static/              # CSS, JS, images
│   ├── auth.py              # Authentication logic
│   ├── database.py          # Database connection
│   ├── main.py              # FastAPI application
│   └── seed.py              # Seed data script
├── tests/                   # Unit tests
├── uploads/                 # File uploads directory
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## Follow-up Engine Rules

The system automatically calculates `next_followup` dates:

1. **Prospecting stage**: `last_contacted + 14 days`
2. **Bid Sent stage**: `last_contacted + 14 days`
3. **Past bid date** (not Won/Lost): `today + 2 business days`

Follow-up dates are recalculated whenever `last_contacted` or `stage` changes.

## Stopping the Application

1. Press `Ctrl+C` in the terminal running uvicorn
2. Deactivate virtual environment: `deactivate`
3. Optionally stop PostgreSQL: `brew services stop postgresql@15`

## License

Proprietary - Internal Use Only

---

**SQLite (quick dev) setup**

If you don't have Postgres available, the project now defaults to a local
SQLite DB for development. The SQLite DB file is `triumphos_dev.db` in the
project root by default (or use `DATABASE_URL` to override).

Exact commands to use for SQLite dev:

- Delete the sqlite DB file (start fresh):
```bash
rm -f triumphos_dev.db
```

- (Optional) run Alembic migrations against the SQLite dev DB:
```bash
# Ensure DATABASE_URL is not set or points to sqlite:///./triumphos_dev.db
source venv/bin/activate
alembic upgrade head
```

- Seed data (this will always create/update the default demo users and
	print their credentials):
```bash
source venv/bin/activate
python -m app.seed
```

- Start the app (it will auto-create tables for SQLite if migrations haven't
	been run):
```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Notes:
- The app will fail loudly on startup if the database cannot be initialized.
- Default dev credentials printed by `app.seed` are:
	- admin@triumphos.com / admin123
	- sarah.sales@triumphos.com / sales123
	- mike.estimator@triumphos.com / estimate123

