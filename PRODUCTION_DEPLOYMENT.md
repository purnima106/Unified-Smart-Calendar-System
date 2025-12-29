# Production Deployment Guide

## Files/Folders to Remove for Production

### ❌ Remove These (Development/Testing Only)

1. **Test Files & Scripts:**
   - `backend/tests/` (entire folder)
   - `backend/test_ms_sync_inline.py`
   - `backend/simple_test.py`
   - `backend/test_report_*.json`
   - `verify_testing_setup.py`
   - `run_tests.bat`
   - `run_tests.sh`

2. **Debug & Diagnostic Scripts:**
   - `backend/debug_microsoft_sync.py`
   - `backend/diagnose_sync_issue.py`
   - `backend/check_microsoft_events.py`
   - `backend/scripts/debug_get_events.py`
   - `backend/scripts/list_future_events.py`
   - `backend/scripts/remove_duplicate_mirror_mappings.py` (one-time migration script)

3. **Development Documentation (Optional - can keep in separate docs folder):**
   - `MANUAL_TEST_CHECKLIST.md`
   - `TESTING_SUMMARY.md`
   - `MICROSOFT_DISABLED_GUIDE.md`
   - `MULTI_GOOGLE_ACCOUNTS_GUIDE.md`
   - `NOTIFICATION_SAFETY.md`
   - `OAUTH_SETUP_GUIDE.md`
   - `backend/setup_instructions.md`
   - `backend/tests/README.md`

4. **Session Storage (Use Production Session Storage Instead):**
   - `backend/flask_session/` (folder)
   - `flask_session/` (root folder)
   - These are already in `.gitignore` - Flask will create them if needed, but use Redis/database sessions in production

5. **Migration Scripts (One-time use, keep for reference but not needed in production):**
   - `backend/migrate_synced_to_mirror.py`
   - `backend/create_event_mirror_mapping_table.py`
   - `backend/reset_database.py` (keep only if you need admin reset functionality)

### ✅ Keep These (Required for Production)

1. **Core Application:**
   - `backend/app.py`
   - `backend/config.py`
   - `backend/__init__.py`
   - `backend/init_db.py` (for initial database setup)
   - `backend/requirements.txt`
   - `backend/env.example` (as template)

2. **Application Code:**
   - `backend/controllers/`
   - `backend/models/`
   - `backend/services/`
   - `backend/utils/`

3. **Frontend:**
   - `frontend/` (entire folder, except `node_modules/` which will be installed via `npm install`)

4. **Essential Documentation:**
   - `README.md` (main project README)
   - `backend/README.md` (if it contains setup instructions)

5. **Configuration:**
   - `.gitignore`
   - `package.json` and `package-lock.json` (frontend)
   - `vite.config.js`, `tailwind.config.js`, etc.

## Production Deployment Checklist

### 1. Environment Setup
- [ ] Set production environment variables (`.env` file with production values)
- [ ] Configure production database (PostgreSQL)
- [ ] Set up production session storage (Redis recommended)
- [ ] Configure production OAuth redirect URLs
- [ ] Set `FLASK_ENV=production` or `FLASK_ENV=production`

### 2. Code Cleanup
- [ ] Remove all test files listed above
- [ ] Remove debug scripts
- [ ] Remove development-only documentation (or move to separate `docs/` folder)
- [ ] Clean up `__pycache__/` folders (will be regenerated)

### 3. Security
- [ ] Ensure `.env` is in `.gitignore` (already done)
- [ ] Use strong secret keys for Flask sessions
- [ ] Enable HTTPS in production
- [ ] Configure CORS properly for production domain
- [ ] Review and remove any hardcoded credentials

### 4. Database
- [ ] Run migrations if needed
- [ ] Initialize database with `backend/init_db.py` (if first deployment)
- [ ] Backup existing data before migration

### 5. Session Storage
- [ ] Configure Redis or database-backed sessions (don't use file-based `flask_session/`)
- [ ] Update Flask config to use production session storage

### 6. Build & Deploy
- [ ] Install production dependencies: `pip install -r backend/requirements.txt`
- [ ] Build frontend: `cd frontend && npm install && npm run build`
- [ ] Configure web server (Nginx/Apache) to serve static files
- [ ] Set up WSGI server (Gunicorn/uWSGI) for Flask backend
- [ ] Configure process manager (systemd/supervisor)

## Recommended Production Structure

```
production/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── __init__.py
│   ├── init_db.py
│   ├── requirements.txt
│   ├── controllers/
│   ├── models/
│   ├── services/
│   └── utils/
├── frontend/
│   ├── dist/          # Built frontend files
│   └── ...            # Source files (optional in production)
├── .env               # Production environment variables
└── README.md          # Main documentation
```

## Session Storage Configuration

### Option 1: Redis (Recommended)
```python
# In config.py
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.from_url('redis://localhost:6379')
```

### Option 2: Database-backed Sessions
```python
# In config.py
SESSION_TYPE = 'sqlalchemy'
SESSION_SQLALCHEMY_TABLE = 'sessions'
```

### Option 3: File-based (NOT Recommended for Production)
- Only use for development
- File-based sessions don't scale and can cause issues with multiple workers

## Quick Cleanup Script

You can create a script to remove development files:

```bash
# Remove test files
rm -rf backend/tests/
rm -f backend/test_*.py
rm -f backend/simple_test.py
rm -f verify_testing_setup.py
rm -f run_tests.bat run_tests.sh

# Remove debug scripts
rm -f backend/debug_*.py
rm -f backend/diagnose_*.py
rm -f backend/check_*.py
rm -rf backend/scripts/

# Remove development docs (optional)
rm -f MANUAL_TEST_CHECKLIST.md
rm -f TESTING_SUMMARY.md
rm -f MICROSOFT_DISABLED_GUIDE.md
rm -f MULTI_GOOGLE_ACCOUNTS_GUIDE.md
rm -f NOTIFICATION_SAFETY.md
rm -f OAUTH_SETUP_GUIDE.md
rm -f backend/setup_instructions.md

# Remove session folders (will be recreated if needed, but use Redis in production)
rm -rf backend/flask_session/
rm -rf flask_session/

# Remove test reports
rm -f backend/test_report_*.json
```

## Notes

- **Keep in Git, Remove from Production**: You can keep test files in your Git repository but exclude them from production deployments using `.dockerignore` or deployment scripts
- **Documentation**: Consider moving development docs to a `docs/` folder that's kept in Git but not deployed
- **Session Storage**: The `flask_session/` folder is already in `.gitignore`, but make sure to configure proper session storage in production

