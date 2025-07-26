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

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found. Creating template...")
        create_env_template()
        return False
    
    # Check for required variables
    required_vars = ["MONGODB_URL", "MONGODB_DATABASE"]
    env_content = env_file.read_text()
    
    missing = []
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables in .env: {', '.join(missing)}")
        return False
    
    print("✓ .env file configured")
    return True

def create_env_template():
    """Create a template .env file."""
    template = """# ProScrape Environment Configuration

# MongoDB Atlas Connection (REQUIRED)
MONGODB_URL=mongodb+srv://your-username:your-password@your-cluster.mongodb.net/
MONGODB_DATABASE=proscrape

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Redis Configuration (handled by Docker)
REDIS_URL=redis://localhost:6379/0

# Optional: Proxy Configuration
ROTATE_PROXIES=false
PROXY_LIST=

# Optional: Scraping Configuration  
DOWNLOAD_DELAY=1.5
CONCURRENT_REQUESTS_PER_DOMAIN=1
"""
    
    with open(".env", "w") as f:
        f.write(template)
    
    print("📝 Created .env template. Please edit it with your MongoDB Atlas credentials.")

def start_services(services="basic"):
    """Start Docker services."""
    print("\n==> Starting containerized services...")
    
    if not check_docker() or not check_env_file():
        return False
    
    cmd = ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"]
    
    if services == "basic":
        # Start only API and Redis
        cmd.extend(["redis", "api", "celery_worker"])
    elif services == "full":
        # Start all services including monitoring
        cmd.append("--profile")
        cmd.append("full")
    
    try:
        run_command(cmd)
        
        print("\n⏳ Waiting for services to be ready...")
        time.sleep(5)
        
        # Check service health
        check_services()
        
        print("\n✅ Services started successfully!")
        print("\n📍 Available endpoints:")
        print("   • API: http://localhost:8000")
        print("   • Health: http://localhost:8000/health")
        print("   • API Docs: http://localhost:8000/docs")
        if services == "full":
            print("   • Flower: http://localhost:5555")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start services: {e}")
        return False

def stop_services():
    """Stop Docker services."""
    print("\n🛑 Stopping containerized services...")
    
    try:
        run_command(["docker-compose", "-f", "docker-compose.dev.yml", "down"])
        print("✅ Services stopped successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to stop services: {e}")
        return False

def check_services():
    """Check if services are running properly."""
    print("\n🔍 Checking service health...")
    
    # Check Redis
    try:
        result = run_command(["docker", "exec", "proscrape_redis_dev", "redis-cli", "ping"], capture_output=True)
        if "PONG" in result.stdout:
            print("   ✓ Redis: Healthy")
        else:
            print("   ❌ Redis: Not responding")
    except:
        print("   ❌ Redis: Container not found")
    
    # Check API
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ API: Healthy")
        else:
            print(f"   ❌ API: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ API: Not responding ({e})")

def show_logs(service=None, follow=False):
    """Show logs for services."""
    print(f"\n📋 Showing logs {'(following)' if follow else ''}...")
    
    cmd = ["docker-compose", "-f", "docker-compose.dev.yml", "logs"]
    
    if follow:
        cmd.append("-f")
    
    if service:
        cmd.append(service)
    
    try:
        run_command(cmd, check=False)
    except KeyboardInterrupt:
        print("\n📋 Logs stopped.")

def restart_services():
    """Restart services."""
    print("\n🔄 Restarting services...")
    stop_services()
    time.sleep(2)
    start_services()

def start_frontend():
    """Instructions for starting frontend."""
    print("\n🌐 To start the frontend locally:")
    print("   1. Open a new terminal")
    print("   2. cd frontend")
    print("   3. npm install  # (if not done yet)")
    print("   4. npm run dev")
    print("   5. Open http://localhost:5174")
    print("\n💡 The frontend will connect to the containerized API at http://localhost:8000")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ProScrape Development Environment Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument("--full", action="store_true", help="Start all services including monitoring")
    
    # Other commands
    subparsers.add_parser("stop", help="Stop services")
    subparsers.add_parser("restart", help="Restart services")
    subparsers.add_parser("status", help="Check service status")
    subparsers.add_parser("frontend", help="Show frontend setup instructions")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("service", nargs="?", help="Specific service name")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "start":
        services = "full" if args.full else "basic"
        success = start_services(services)
        if success:
            start_frontend()
    
    elif args.command == "stop":
        stop_services()
    
    elif args.command == "restart":
        restart_services()
    
    elif args.command == "status":
        check_services()
    
    elif args.command == "logs":
        show_logs(args.service, args.follow)
    
    elif args.command == "frontend":
        start_frontend()

if __name__ == "__main__":
    main()