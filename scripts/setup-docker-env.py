#!/usr/bin/env python3
"""
Docker Environment Setup Script for ProScrape
This script helps set up the Docker development environment with proper configuration.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color


class DockerSetup:
    """Docker environment setup manager."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env.docker"
        self.env_example = self.project_root / ".env.docker.example"
        self.compose_file = self.project_root / "docker-compose.dev.yml"
        
    def log(self, level: str, message: str):
        """Log a message with color coding."""
        colors = {
            'INFO': Colors.BLUE,
            'SUCCESS': Colors.GREEN,
            'WARNING': Colors.YELLOW,
            'ERROR': Colors.RED,
            'DEBUG': Colors.PURPLE
        }
        color = colors.get(level.upper(), Colors.NC)
        print(f"{color}[{level.upper()}]{Colors.NC} {message}")
    
    def run_command(self, command: List[str], capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            if capture_output:
                result = subprocess.run(command, capture_output=True, text=True, check=True)
            else:
                result = subprocess.run(command, check=True)
            return result
        except subprocess.CalledProcessError as e:
            self.log('ERROR', f"Command failed: {' '.join(command)}")
            if capture_output and e.stdout:
                print(e.stdout)
            if capture_output and e.stderr:
                print(e.stderr)
            raise
    
    def check_prerequisites(self) -> bool:
        """Check if Docker and docker-compose are installed and running."""
        self.log('INFO', "Checking prerequisites...")
        
        # Check Docker
        try:
            result = self.run_command(['docker', '--version'], capture_output=True)
            self.log('SUCCESS', f"Docker found: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.log('ERROR', "Docker is not installed or not in PATH")
            return False
        
        # Check docker-compose
        try:
            result = self.run_command(['docker-compose', '--version'], capture_output=True)
            self.log('SUCCESS', f"Docker Compose found: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.log('ERROR', "Docker Compose is not installed or not in PATH")
            return False
        
        # Check if Docker daemon is running
        try:
            self.run_command(['docker', 'info'], capture_output=True)
            self.log('SUCCESS', "Docker daemon is running")
        except subprocess.CalledProcessError:
            self.log('ERROR', "Docker daemon is not running. Please start Docker.")
            return False
        
        return True
    
    def create_env_file(self) -> bool:
        """Create environment file from example."""
        if self.env_file.exists():
            self.log('INFO', f"Environment file {self.env_file.name} already exists")
            return True
        
        if not self.env_example.exists():
            self.log('ERROR', f"Example environment file {self.env_example.name} not found")
            return False
        
        self.log('INFO', f"Creating {self.env_file.name} from {self.env_example.name}")
        try:
            shutil.copy2(self.env_example, self.env_file)
            self.log('SUCCESS', f"Created {self.env_file.name}")
            self.log('WARNING', f"Please review and customize the environment variables in {self.env_file.name}")
            return True
        except Exception as e:
            self.log('ERROR', f"Failed to create environment file: {e}")
            return False
    
    def create_directories(self) -> bool:
        """Create necessary directories."""
        directories = [
            self.project_root / "logs",
            self.project_root / "backups",
            self.project_root / "data" / "mongodb",
            self.project_root / "data" / "postgres",
            self.project_root / "data" / "redis",
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                self.log('INFO', f"Created directory: {directory.relative_to(self.project_root)}")
            except Exception as e:
                self.log('ERROR', f"Failed to create directory {directory}: {e}")
                return False
        
        return True
    
    def create_docker_volumes(self) -> bool:
        """Create Docker volumes."""
        volumes = [
            "proscrape_mongodb_data",
            "proscrape_postgres_data",
            "proscrape_redis_data",
            "proscrape_logs"
        ]
        
        self.log('INFO', "Creating Docker volumes...")
        for volume in volumes:
            try:
                # Check if volume exists
                result = self.run_command(['docker', 'volume', 'ls', '-q', '-f', f'name={volume}'], capture_output=True)
                if volume in result.stdout:
                    self.log('INFO', f"Volume {volume} already exists")
                else:
                    self.run_command(['docker', 'volume', 'create', volume])
                    self.log('SUCCESS', f"Created volume: {volume}")
            except subprocess.CalledProcessError as e:
                self.log('ERROR', f"Failed to create volume {volume}: {e}")
                return False
        
        return True
    
    def pull_images(self) -> bool:
        """Pull required Docker images."""
        if not self.compose_file.exists():
            self.log('WARNING', f"Docker Compose file {self.compose_file.name} not found, skipping image pull")
            return True
        
        self.log('INFO', "Pulling Docker images...")
        try:
            self.run_command([
                'docker-compose', 
                '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'pull'
            ])
            self.log('SUCCESS', "Docker images pulled successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.log('ERROR', f"Failed to pull Docker images: {e}")
            return False
    
    def validate_configuration(self) -> bool:
        """Validate Docker configuration."""
        if not self.compose_file.exists():
            self.log('ERROR', f"Docker Compose file {self.compose_file.name} not found")
            return False
        
        self.log('INFO', "Validating Docker Compose configuration...")
        try:
            self.run_command([
                'docker-compose',
                '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'config'
            ], capture_output=True)
            self.log('SUCCESS', "Docker Compose configuration is valid")
            return True
        except subprocess.CalledProcessError as e:
            self.log('ERROR', f"Docker Compose configuration is invalid: {e}")
            return False
    
    def setup_networking(self) -> bool:
        """Set up Docker networks."""
        network_name = "proscrape_network"
        
        self.log('INFO', f"Setting up Docker network: {network_name}")
        try:
            # Check if network exists
            result = self.run_command(['docker', 'network', 'ls', '-q', '-f', f'name={network_name}'], capture_output=True)
            if network_name in result.stdout:
                self.log('INFO', f"Network {network_name} already exists")
            else:
                self.run_command(['docker', 'network', 'create', network_name])
                self.log('SUCCESS', f"Created network: {network_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.log('ERROR', f"Failed to create network {network_name}: {e}")
            return False
    
    def generate_secrets(self) -> Dict[str, str]:
        """Generate secure secrets for the application."""
        import secrets
        import string
        
        def generate_password(length: int = 32) -> str:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        
        secrets_dict = {
            'MONGODB_ROOT_PASSWORD': generate_password(),
            'POSTGRES_PASSWORD': generate_password(),
            'REDIS_PASSWORD': generate_password(),
            'JWT_SECRET_KEY': generate_password(64),
            'API_KEY': generate_password(32)
        }
        
        self.log('INFO', "Generated secure secrets")
        return secrets_dict
    
    def update_env_with_secrets(self, secrets: Dict[str, str]) -> bool:
        """Update environment file with generated secrets."""
        if not self.env_file.exists():
            self.log('ERROR', "Environment file does not exist")
            return False
        
        try:
            # Read current env file
            with open(self.env_file, 'r') as f:
                lines = f.readlines()
            
            # Update with secrets
            updated_lines = []
            for line in lines:
                line_updated = False
                for key, value in secrets.items():
                    if line.startswith(f"{key}=") or line.startswith(f"#{key}="):
                        updated_lines.append(f"{key}={value}\n")
                        line_updated = True
                        break
                
                if not line_updated:
                    updated_lines.append(line)
            
            # Write updated env file
            with open(self.env_file, 'w') as f:
                f.writelines(updated_lines)
            
            self.log('SUCCESS', "Updated environment file with generated secrets")
            return True
        
        except Exception as e:
            self.log('ERROR', f"Failed to update environment file: {e}")
            return False
    
    def print_summary(self):
        """Print setup summary and next steps."""
        print(f"\n{Colors.GREEN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}ProScrape Docker Environment Setup Complete!{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        
        print(f"\n{Colors.CYAN}Next Steps:{Colors.NC}")
        print(f"1. Review and customize environment variables in {Colors.YELLOW}{self.env_file.name}{Colors.NC}")
        print(f"2. Start the development environment:")
        print(f"   {Colors.WHITE}./scripts/docker-dev.sh start{Colors.NC}")
        print(f"   {Colors.WHITE}# or on Windows:{Colors.NC}")
        print(f"   {Colors.WHITE}scripts\\docker-dev.bat start{Colors.NC}")
        
        print(f"\n{Colors.CYAN}Service URLs (after starting):{Colors.NC}")
        print(f"  API:           {Colors.WHITE}http://localhost:8000{Colors.NC}")
        print(f"  Frontend:      {Colors.WHITE}http://localhost:3000{Colors.NC}")
        print(f"  Flower:        {Colors.WHITE}http://localhost:5555{Colors.NC}")
        print(f"  API Docs:      {Colors.WHITE}http://localhost:8000/docs{Colors.NC}")
        
        print(f"\n{Colors.CYAN}Useful Commands:{Colors.NC}")
        print(f"  Status:        {Colors.WHITE}./scripts/docker-dev.sh status{Colors.NC}")
        print(f"  Logs:          {Colors.WHITE}./scripts/docker-dev.sh logs{Colors.NC}")
        print(f"  Stop:          {Colors.WHITE}./scripts/docker-dev.sh stop{Colors.NC}")
        print(f"  Health Check:  {Colors.WHITE}./scripts/docker-dev.sh health{Colors.NC}")
        
        print(f"\n{Colors.YELLOW}Note: Generated secure passwords have been added to {self.env_file.name}{Colors.NC}")
        print(f"{Colors.YELLOW}Keep this file secure and do not commit it to version control.{Colors.NC}")
    
    def setup(self) -> bool:
        """Run the complete setup process."""
        self.log('INFO', "Starting ProScrape Docker environment setup...")
        
        steps = [
            ("Checking prerequisites", self.check_prerequisites),
            ("Creating environment file", self.create_env_file),
            ("Creating directories", self.create_directories),
            ("Setting up networking", self.setup_networking),
            ("Creating Docker volumes", self.create_docker_volumes),
            ("Validating configuration", self.validate_configuration),
            ("Pulling Docker images", self.pull_images),
        ]
        
        for step_name, step_func in steps:
            self.log('INFO', f"Step: {step_name}")
            if not step_func():
                self.log('ERROR', f"Setup failed at step: {step_name}")
                return False
        
        # Generate and update secrets
        secrets = self.generate_secrets()
        if not self.update_env_with_secrets(secrets):
            self.log('WARNING', "Failed to update secrets, using defaults")
        
        self.log('SUCCESS', "Docker environment setup completed successfully!")
        self.print_summary()
        return True


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print("ProScrape Docker Environment Setup")
        print("Usage: python setup-docker-env.py")
        print("This script sets up the Docker development environment for ProScrape.")
        return
    
    setup_manager = DockerSetup()
    
    try:
        success = setup_manager.setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        setup_manager.log('WARNING', "Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        setup_manager.log('ERROR', f"Unexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()