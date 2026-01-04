#!/usr/bin/env python3
"""
SkillBridge Suite Backend Setup Script
Installs dependencies and sets up the development environment
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major != 3 or version.minor < 11:
        print(f"❌ Python 3.11+ required. Current version: {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def setup_virtual_environment():
    """Set up Python virtual environment"""
    if os.path.exists("venv"):
        print("📁 Virtual environment already exists")
        return True
    
    return run_command("python -m venv venv", "Creating virtual environment")

def install_dependencies(dev=False):
    """Install Python dependencies"""
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_cmd = "venv/bin/pip"
    
    # Upgrade pip first
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    req_file = "requirements-dev.txt" if dev else "requirements.txt"
    return run_command(f"{pip_cmd} install -r {req_file}", f"Installing dependencies from {req_file}")

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if os.path.exists(".env"):
        print("📄 .env file already exists")
        return True
    
    if os.path.exists(".env.example"):
        try:
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                dst.write(src.read())
            print("✅ Created .env file from template")
            print("⚠️  Please update .env with your actual configuration values")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("❌ .env.example template not found")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ["credentials", "ssl", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    return True

def main():
    """Main setup function"""
    print("🚀 SkillBridge Suite Backend Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found. Please run this script from the backend directory.")
        sys.exit(1)
    
    # Parse command line arguments
    dev_mode = "--dev" in sys.argv
    skip_venv = "--no-venv" in sys.argv
    
    print(f"📋 Setup mode: {'Development' if dev_mode else 'Production'}")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup virtual environment (unless skipped)
    if not skip_venv:
        if not setup_virtual_environment():
            sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(dev=dev_mode):
        sys.exit(1)
    
    # Create configuration files
    if not create_env_file():
        print("⚠️  Continuing without .env file...")
    
    # Create necessary directories
    create_directories()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Update .env file with your configuration")
    print("2. Add Firebase service account to credentials/")
    print("3. Run the application:")
    
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\python app\\main.py")
    else:  # Unix/Linux/macOS
        print("   source venv/bin/activate")
        print("   python app/main.py")
    
    print("\n🐳 Or use Docker:")
    print("   docker-compose up -d")

if __name__ == "__main__":
    main()