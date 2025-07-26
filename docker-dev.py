#!/usr/bin/env python3
"""
ProScrape Docker Development Manager
Simplified Docker management for development workflow
"""

import subprocess
import sys
import time
import argparse
import os
from pathlib import Path

class DockerDevManager:
    def __init__(self):
        self.compose_files = [
            "docker-compose.yml",
            "docker-compose.dev.yml"
        ]
        self.project_name = "proscrape"
    
    def run_command(self, cmd, check=True, capture_output=False):
        """Run a command and handle output."""
        print(f"Running: {' '.join(cmd)}")
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        else:
            result = subprocess.run(cmd, check=check)
            return result
    
    def get_compose_cmd(self, *args):
        """Build docker-compose command with proper files."""
        cmd = ["docker-compose"]
        for file in self.compose_files:
            cmd.extend(["-f", file])
        cmd.extend(["-p", self.project_name])
        cmd.extend(args)
        return cmd
    
    def check_prerequisites(self):
        """Check if Docker and required files exist."""
        print("==> Checking prerequisites...")
        
        # Check Docker
        try:
            result = self.run_command(["docker", "--version"], capture_output=True)
            if result.returncode == 0:
                print(f"[OK] {result.stdout.strip()}")
            else:
                print("[ERROR] Docker not found")
                return False
        except FileNotFoundError:
            print("[ERROR] Docker not found. Please install Docker Desktop.")
            return False
        
        # Check docker-compose files
        for file in self.compose_files:
            if not Path(file).exists():
                print(f"[ERROR] Missing {file}")
                return False
            print(f"[OK] Found {file}")
        
        # Check .env file
        if not Path(".env").exists():
            print("[WARNING] .env file not found. Using defaults.")
        else:
            print("[OK] Found .env file")
        
        return True
    
    def build_services(self, services=None):
        """Build Docker services."""
        print("\n==> Building services...")
        
        cmd = self.get_compose_cmd("build")
        if services:
            cmd.extend(services)
        
        try:
            self.run_command(cmd)
            print("[OK] Build completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Build failed: {e}")
            return False
    
    def start_services(self, services=None):
        """Start Docker services."""
        print("\n==> Starting services...")
        
        # Default services for development
        if not services:
            services = ["redis", "api", "celery_worker", "flower"]
        
        cmd = self.get_compose_cmd("up", "-d") + services
        
        try:
            self.run_command(cmd)
            
            print("\n==> Waiting for services to be ready...")
            time.sleep(5)
            
            self.check_services()
            
            print("\n[OK] Services started successfully!")
            self.show_endpoints()
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to start services: {e}")
            return False
    
    def stop_services(self):
        """Stop Docker services."""
        print("\n==> Stopping services...")
        
        try:
            self.run_command(self.get_compose_cmd("down"))
            print("[OK] Services stopped successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to stop services: {e}")
            return False
    
    def restart_services(self, services=None):
        """Restart specific services or all."""
        print("\n==> Restarting services...")
        
        if services:
            cmd = self.get_compose_cmd("restart") + services
        else:
            cmd = self.get_compose_cmd("restart")
        
        try:
            self.run_command(cmd)
            print("[OK] Services restarted successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to restart services: {e}")
            return False
    
    def check_services(self):
        """Check service health."""
        print("\n==> Checking service health...")
        
        # Check API
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("   [OK] API: Healthy")
                data = response.json()
                print(f"        Status: {data.get('status')}")
                print(f"        Database: {data.get('database')}")
            else:
                print(f"   [ERROR] API: HTTP {response.status_code}")
        except Exception as e:
            print(f"   [WARNING] API: Not responding ({e})")
        
        # Check Flower
        try:
            import requests
            response = requests.get("http://localhost:5555", timeout=5)
            if response.status_code == 200:
                print("   [OK] Flower: Accessible")
            else:
                print(f"   [WARNING] Flower: HTTP {response.status_code}")
        except Exception as e:
            print(f"   [WARNING] Flower: Not responding ({e})")
    
    def show_logs(self, service=None, follow=False):
        """Show service logs."""
        print(f"\n==> Showing logs {'(following)' if follow else ''}...")
        
        cmd = self.get_compose_cmd("logs")
        if follow:
            cmd.append("-f")
        if service:
            cmd.append(service)
        
        try:
            self.run_command(cmd, check=False)
        except KeyboardInterrupt:
            print("\n[INFO] Logs stopped")
    
    def show_status(self):
        """Show service status."""
        print("\n==> Service status:")
        
        try:
            self.run_command(self.get_compose_cmd("ps"))
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to get service status")
    
    def show_endpoints(self):
        """Show available endpoints."""
        print("\n==> Available endpoints:")
        print("   - API: http://localhost:8000")
        print("   - API Health: http://localhost:8000/health")
        print("   - API Docs: http://localhost:8000/docs")
        print("   - Flower: http://localhost:5555 (admin:dev)")
        print("\n==> Frontend setup:")
        print("   1. Open new terminal")
        print("   2. cd frontend")
        print("   3. npm run dev")
        print("   4. Open http://localhost:5174")
    
    def cleanup(self):
        """Clean up Docker resources."""
        print("\n==> Cleaning up Docker resources...")
        
        try:
            # Stop and remove containers
            self.run_command(self.get_compose_cmd("down", "-v"))
            
            # Remove unused images
            self.run_command(["docker", "image", "prune", "-f"])
            
            # Remove unused volumes
            self.run_command(["docker", "volume", "prune", "-f"])
            
            print("[OK] Cleanup completed!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Cleanup failed: {e}")
            return False

def main():
    """Main entry point."""
    manager = DockerDevManager()
    
    parser = argparse.ArgumentParser(description="ProScrape Docker Development Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument("--build", action="store_true", help="Build before starting")
    start_parser.add_argument("--services", nargs="+", help="Specific services to start")
    
    # Other commands
    subparsers.add_parser("stop", help="Stop services")
    subparsers.add_parser("restart", help="Restart services")
    subparsers.add_parser("status", help="Show service status")
    subparsers.add_parser("health", help="Check service health")
    subparsers.add_parser("endpoints", help="Show available endpoints")
    subparsers.add_parser("cleanup", help="Clean up Docker resources")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build services")
    build_parser.add_argument("services", nargs="*", help="Specific services to build")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("service", nargs="?", help="Specific service name")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Check prerequisites for most commands
    if args.command not in ["cleanup"] and not manager.check_prerequisites():
        sys.exit(1)
    
    if args.command == "start":
        if args.build:
            if not manager.build_services(args.services):
                sys.exit(1)
        
        success = manager.start_services(args.services)
        if not success:
            sys.exit(1)
    
    elif args.command == "stop":
        manager.stop_services()
    
    elif args.command == "restart":
        manager.restart_services()
    
    elif args.command == "build":
        success = manager.build_services(args.services if args.services else None)
        if not success:
            sys.exit(1)
    
    elif args.command == "status":
        manager.show_status()
    
    elif args.command == "health":
        manager.check_services()
    
    elif args.command == "logs":
        manager.show_logs(args.service, args.follow)
    
    elif args.command == "endpoints":
        manager.show_endpoints()
    
    elif args.command == "cleanup":
        manager.cleanup()

if __name__ == "__main__":
    main()