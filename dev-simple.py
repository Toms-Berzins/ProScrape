#!/usr/bin/env python3
"""
ProScrape Development Environment Manager
Manages Docker containers for API/Redis and local frontend development.
"""

import subprocess
import sys
import time
import argparse
import os
from pathlib import Path

def run_command(cmd, check=True, capture_output=False):
    """Run a command and handle output."""
    print(f"Running: {' '.join(cmd)}")
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    else:
        result = subprocess.run(cmd, check=check)
        return result

def check_docker():
    """Check if Docker is available."""
    try:
        result = run_command(["docker", "--version"], capture_output=True)
        if result.returncode == 0:
            print(f"[OK] {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("[ERROR] Docker not found. Please install Docker Desktop.")
    return False

def start_services():
    """Start Docker services."""
    print("\n==> Starting containerized services...")
    
    if not check_docker():
        return False
    
    cmd = ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d", "redis", "api"]
    
    try:
        run_command(cmd)
        
        print("\n==> Waiting for services to be ready...")
        time.sleep(10)
        
        print("\n[OK] Services started successfully!")
        print("\n==> Available endpoints:")
        print("   - API: http://localhost:8000")
        print("   - Health: http://localhost:8000/health")
        print("   - API Docs: http://localhost:8000/docs")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to start services: {e}")
        return False

def stop_services():
    """Stop Docker services."""
    print("\n==> Stopping containerized services...")
    
    try:
        run_command(["docker-compose", "-f", "docker-compose.dev.yml", "down"])
        print("[OK] Services stopped successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to stop services: {e}")
        return False

def check_services():
    """Check if services are running properly."""
    print("\n==> Checking service health...")
    
    # Check API
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("   [OK] API: Healthy")
            print(f"   Response: {response.text}")
        else:
            print(f"   [ERROR] API: HTTP {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] API: Not responding ({e})")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python dev-simple.py [start|stop|status]")
        return
    
    command = sys.argv[1]
    
    if command == "start":
        success = start_services()
        if success:
            print("\n==> Frontend setup:")
            print("   1. Open new terminal")
            print("   2. cd frontend")
            print("   3. npm run dev")
            print("   4. Open http://localhost:5174")
    
    elif command == "stop":
        stop_services()
    
    elif command == "status":
        check_services()
    
    else:
        print("Unknown command. Use: start, stop, or status")

if __name__ == "__main__":
    main()