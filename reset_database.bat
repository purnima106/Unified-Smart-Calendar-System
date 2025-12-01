@echo off
echo ========================================
echo Database Reset Script
echo ========================================
echo.
echo WARNING: This will delete ALL data!
echo.
cd backend
python reset_database.py
pause

