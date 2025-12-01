#!/bin/bash
# Test Execution Script for Unified Smart Calendar System
# Run all automated tests and generate reports

echo "=========================================="
echo "Unified Smart Calendar System - Test Suite"
echo "=========================================="
echo ""

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found"
    exit 1
fi

cd backend

# Check Python environment
echo "Checking Python environment..."
if ! command -v python &> /dev/null; then
    echo "Error: Python not found"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate 2>/dev/null || .venv/Scripts/activate 2>/dev/null

# Install test dependencies if needed
echo "Checking dependencies..."
pip install -q requests 2>/dev/null || pip install requests

# Run feature verification
echo ""
echo "=========================================="
echo "Step 1: Feature Verification"
echo "=========================================="
python tests/verify_features.py
VERIFY_EXIT=$?

# Setup test data
echo ""
echo "=========================================="
echo "Step 2: Test Data Setup"
echo "=========================================="
python tests/test_data_setup.py
SETUP_EXIT=$?

# Run API tests
echo ""
echo "=========================================="
echo "Step 3: API Endpoint Tests"
echo "=========================================="
python tests/test_runner.py
TEST_EXIT=$?

# Summary
echo ""
echo "=========================================="
echo "Test Execution Summary"
echo "=========================================="
echo "Feature Verification: $([ $VERIFY_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo "Test Data Setup: $([ $SETUP_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo "API Tests: $([ $TEST_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo ""

if [ $VERIFY_EXIT -eq 0 ] && [ $SETUP_EXIT -eq 0 ] && [ $TEST_EXIT -eq 0 ]; then
    echo "All automated tests passed!"
    exit 0
else
    echo "Some tests failed. Please review the output above."
    exit 1
fi

