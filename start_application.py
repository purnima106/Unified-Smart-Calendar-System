#!/usr/bin/env python3
"""
Quick start script for Unified Smart Calendar System
This script helps you start both backend and frontend services
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check Python dependencies
    try:
        import flask
        import flask_cors
        import flask_login
        import flask_sqlalchemy
        import flask_session
        print("✅ Python dependencies found")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("Please run: pip install -r backend/requirements.txt")
        return False
    
    # Check if Node.js is installed
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
        print("✅ Node.js found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js not found. Please install Node.js from https://nodejs.org/")
        return False
    
    # Check if npm is installed
    try:
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
        print("✅ npm found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ npm not found. Please install npm")
        return False
    
    return True

def check_environment():
    """Check if environment variables are configured"""
    print("\n🔍 Checking environment configuration...")
    
    env_file = Path("backend/.env")
    if not env_file.exists():
        print("❌ .env file not found in backend directory")
        print("Please create backend/.env file with your OAuth credentials")
        print("See backend/setup_instructions.md for details")
        return False
    
    print("✅ .env file found")
    return True

def install_frontend_dependencies():
    """Install frontend dependencies"""
    print("\n📦 Installing frontend dependencies...")
    
    try:
        subprocess.run(["npm", "install"], cwd="frontend", check=True)
        print("✅ Frontend dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install frontend dependencies: {e}")
        return False

def start_backend():
    """Start the backend server"""
    print("\n🚀 Starting backend server...")
    
    try:
        # Change to backend directory
        os.chdir("backend")
        
        # Start the Flask app
        process = subprocess.Popen([
            sys.executable, "app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the server to start
        time.sleep(3)
        
        # Check if the process is still running
        if process.poll() is None:
            print("✅ Backend server started on http://localhost:5000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Backend server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the frontend development server"""
    print("\n🚀 Starting frontend server...")
    
    try:
        # Change to frontend directory
        os.chdir("frontend")
        
        # Start the Vite dev server
        process = subprocess.Popen([
            "npm", "run", "dev"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for the server to start
        time.sleep(5)
        
        # Check if the process is still running
        if process.poll() is None:
            print("✅ Frontend server started on http://localhost:3000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Frontend server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def main():
    """Main function"""
    print("🎯 Unified Smart Calendar System - Quick Start")
    print("=" * 50)
    
    # Store original directory
    original_dir = os.getcwd()
    
    try:
        # Check dependencies
        if not check_dependencies():
            return
        
        # Check environment
        if not check_environment():
            return
        
        # Install frontend dependencies
        if not install_frontend_dependencies():
            return
        
        # Start backend
        backend_process = start_backend()
        if not backend_process:
            return
        
        # Start frontend
        frontend_process = start_frontend()
        if not frontend_process:
            backend_process.terminate()
            return
        
        print("\n🎉 Application started successfully!")
        print("📱 Frontend: http://localhost:3000")
        print("🔧 Backend: http://localhost:5000")
        print("📊 Health Check: http://localhost:5000/health")
        print("\nPress Ctrl+C to stop both servers")
        
        # Open browser
        try:
            webbrowser.open("http://localhost:3000")
        except:
            pass
        
        # Wait for user to stop
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping servers...")
            backend_process.terminate()
            frontend_process.terminate()
            print("✅ Servers stopped")
    
    finally:
        # Return to original directory
        os.chdir(original_dir)

if __name__ == "__main__":
    main()
