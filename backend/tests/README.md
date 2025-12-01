# Testing Infrastructure

This directory contains the testing infrastructure for the Unified Smart Calendar System.

## Test Files

### `test_api_endpoints.py`
Comprehensive API endpoint testing suite. Tests all backend API endpoints including:
- Authentication endpoints (Google, Microsoft OAuth)
- Calendar sync endpoints (Google, Microsoft, All, Bidirectional)
- Calendar operations (events, conflicts, free slots, summary)
- User connections management

**Usage:**
```bash
python tests/test_api_endpoints.py
```

### `test_data_setup.py`
Creates test data for comprehensive testing including:
- Test users (Google, Microsoft, multi-provider)
- Calendar connections
- Test events (including overlapping events for conflict testing)

**Usage:**
```bash
python tests/test_data_setup.py
```

### `test_runner.py`
Main test runner that orchestrates all automated tests:
- Environment verification
- Feature verification
- API endpoint tests
- Test report generation

**Usage:**
```bash
python tests/test_runner.py
```

### `verify_features.py`
Verifies that all required features are implemented:
- Backend models and services
- Frontend components
- API endpoints registration

**Usage:**
```bash
python tests/verify_features.py
```

### `test_notification_safety.py`
Tests notification safety for bidirectional sync (existing test).

## Running Tests

### Quick Start

From project root:

**Windows:**
```bash
run_tests.bat
```

**Linux/Mac:**
```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Manual Execution

1. **Setup test data:**
   ```bash
   cd backend
   python tests/test_data_setup.py
   ```

2. **Run API tests:**
   ```bash
   python tests/test_runner.py
   ```

3. **Verify features:**
   ```bash
   python tests/verify_features.py
   ```

## Test Requirements

### Environment
- Backend server running on `http://localhost:5000`
- PostgreSQL database running
- Python 3.8+
- Required packages: `requests`, `flask`, `sqlalchemy`

### Configuration
- Set `TEST_API_URL` environment variable to override default API URL
- Set `TEST_USER_EMAIL` for user-specific tests

## Test Reports

Test reports are generated in JSON format with timestamps:
- `test_report_YYYYMMDD_HHMMSS.json`

Reports include:
- Test execution times
- Pass/fail status for each test
- Error messages (if any)
- Environment verification results

## Integration with Manual Testing

These automated tests complement the manual testing checklist in `MANUAL_TEST_CHECKLIST.md` and the comprehensive plan in `project.plan.md`.

## Troubleshooting

### Backend Not Running
```bash
cd backend
python app.py
```

### Database Connection Error
- Check PostgreSQL is running
- Verify DATABASE_URL in `.env`
- Ensure database exists

### Import Errors
- Ensure you're running from the correct directory
- Check Python path includes backend directory
- Verify virtual environment is activated

### Test Failures
- Check backend logs for errors
- Verify environment variables are set
- Ensure test data is set up correctly

