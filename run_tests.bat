@echo off
REM Test Execution Script for Unified Smart Calendar System (Windows)
REM Run all automated tests and generate reports

echo ==========================================
echo Unified Smart Calendar System - Test Suite
echo ==========================================
echo.

REM Check if backend directory exists
if not exist "backend" (
    echo Error: backend directory not found
    exit /b 1
)

cd backend

REM Check Python environment
echo Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install test dependencies if needed
echo Checking dependencies...
pip install -q requests 2>nul || pip install requests

REM Run feature verification
echo.
echo ==========================================
echo Step 1: Feature Verification
echo ==========================================
python tests\verify_features.py
set VERIFY_EXIT=%ERRORLEVEL%

REM Setup test data
echo.
echo ==========================================
echo Step 2: Test Data Setup
echo ==========================================
python tests\test_data_setup.py
set SETUP_EXIT=%ERRORLEVEL%

REM Run API tests
echo.
echo ==========================================
echo Step 3: API Endpoint Tests
echo ==========================================
python tests\test_runner.py
set TEST_EXIT=%ERRORLEVEL%

REM Summary
echo.
echo ==========================================
echo Test Execution Summary
echo ==========================================
if %VERIFY_EXIT%==0 (echo Feature Verification: PASS) else (echo Feature Verification: FAIL)
if %SETUP_EXIT%==0 (echo Test Data Setup: PASS) else (echo Test Data Setup: FAIL)
if %TEST_EXIT%==0 (echo API Tests: PASS) else (echo API Tests: FAIL)
echo.

if %VERIFY_EXIT%==0 if %SETUP_EXIT%==0 if %TEST_EXIT%==0 (
    echo All automated tests passed!
    exit /b 0
) else (
    echo Some tests failed. Please review the output above.
    exit /b 1
)

