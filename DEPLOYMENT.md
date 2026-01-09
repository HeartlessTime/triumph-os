# Deployment Guide

## Current Status

✅ **App is deployed and running** on Render at https://triumph-os.onrender.com
✅ **Authentication has been completely removed**
❌ **Database migrations need to be run**

## Issue

Routes that query the database return 500 errors because the database tables don't exist yet:
- `/` (Dashboard) - 500
- `/accounts` - 500
- `/opportunities` - 500
- `/contacts` - 500

Routes that don't need database work fine:
- `/how-to-use` - 200 ✓

## Solution

The database migrations need to be run. This should happen automatically via the `render.yaml` configuration, but Render needs to rebuild the app.

### Option 1: Automatic (Recommended)

Render should automatically detect `render.yaml` and rebuild the app. Once it does:
1. It will run `./build.sh` which installs dependencies and runs Alembic migrations
2. All tables will be created
3. All routes will work

### Option 2: Manual Configuration

If Render doesn't automatically pick up `render.yaml`, configure it manually in the Render dashboard:

1. Go to your Render service dashboard
2. Navigate to "Settings"
3. Set **Build Command** to: `./build.sh`
4. Set **Start Command** to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click "Save Changes"
6. Trigger a manual deploy

### Option 3: Run Migrations Manually

If you have access to Render Shell:
```bash
alembic upgrade head
```

## Verification

After migrations run, test all routes:
```bash
curl -I https://triumph-os.onrender.com/
curl -I https://triumph-os.onrender.com/accounts
curl -I https://triumph-os.onrender.com/opportunities
```

All should return `200 OK`.

## Database Configuration

Ensure DATABASE_URL is set in Render environment variables:
- It should be the **full PostgreSQL connection string**
- Format: `postgresql+psycopg://user:password@host:port/database`
- NOT just the hostname like `dpg-d5fkq92li9vc738qslug-a`

## Files Changed

1. `alembic/versions/001_initial.py` - Removed users table and all user foreign keys
2. `alembic/env.py` - Ensure alembic_version.version_num is VARCHAR(128) before migrations
3. `build.sh` - Runs pip install and Alembic migrations
4. `render.yaml` - Configures Render to use build.sh
5. `app/auth.py`, `app/routes/auth.py` - Deleted (authentication removed)
6. All route files - Removed user checks and authentication

## Recent Fixes

### Alembic Version Table Fix (Latest)
- Updated `alembic/env.py` to automatically ensure `alembic_version.version_num` is VARCHAR(128)
- This prevents errors with revision IDs longer than 32 characters
- The check runs before every migration and safely alters the column if needed

## Next Steps

1. Wait for Render to rebuild (or trigger manual rebuild)
2. Verify DATABASE_URL environment variable is correct
3. Check deployment logs for migration success
4. Test all routes return 200
5. Run seed data if needed: `python -m app.seed`
