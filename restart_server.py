#!/usr/bin/env python3
"""
SkillBridge Suite Backend Restart Script
Stops any running instances and starts a fresh server
"""

import os
import sys
import signal
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def find_and_kill_existing_servers():
    """Find and kill existing Flask servers"""
    try:
        # On Windows, use tasklist and taskkill
        if os.name == 'nt':
            # Find Python processes running on port 8000
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            for line in lines:
                if ':8000' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        try:
                            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                            print(f"✅ Killed process {pid}")
                        except:
                            pass
        else:
            # On Unix-like systems
            subprocess.run(['pkill', '-f', 'python.*run.py'], capture_output=True)
            subprocess.run(['pkill', '-f', 'python.*main.py'], capture_output=True)
            
        time.sleep(2)  # Give processes time to terminate
        
    except Exception as e:
        print(f"⚠️  Could not kill existing servers: {e}")

def start_server():
    """Start the Flask server"""
    try:
        print("🚀 Starting SkillBridge Suite Backend...")
        
        # Add current directory to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import and run the Flask app
        from app import create_app
        
        app = create_app()
        
        port = int(os.environ.get('PORT', 8000))
        debug = os.environ.get('FLASK_ENV') == 'development'
        
        print(f"📍 Server: http://localhost:{port}")
        print(f"🔧 Environment: {'Development' if debug else 'Production'}")
        print(f"📊 Health Check: http://localhost:{port}/health")
        print(f"💼 Job Roles: http://localhost:{port}/roles")
        print("=" * 50)
        
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        print(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)

def main():
    """Main restart function"""
    print("🔄 Restarting SkillBridge Suite Backend...")
    
    # Kill existing servers
    find_and_kill_existing_servers()
    
    # Start new server
    start_server()

if __name__ == '__main__':
    main()