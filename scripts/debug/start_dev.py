#!/usr/bin/env python3
"""
Development server startup script for SkillBridge Backend
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    print("🚀 Starting SkillBridge Backend Development Server...")
    print(f"📁 Working directory: {backend_dir}")
    
    # Check if .env file exists
    env_file = backend_dir / '.env'
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("Please create a .env file based on .env.example")
        sys.exit(1)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("Consider activating the virtual environment first:")
        print("  source venv/bin/activate  # On Linux/Mac")
        print("  venv\\Scripts\\activate     # On Windows")
        print()
    
    # Load environment variables to check configuration
    from dotenv import load_dotenv
    load_dotenv()
    
    port = os.environ.get('PORT', '8000')
    flask_env = os.environ.get('FLASK_ENV', 'development')
    
    print(f"🔧 Configuration:")
    print(f"   Port: {port}")
    print(f"   Environment: {flask_env}")
    print(f"   CORS Origins: {os.environ.get('CORS_ORIGINS', 'Not set')}")
    print()
    
    # Start the Flask application
    try:
        print(f"🌐 Starting server on http://localhost:{port}")
        print("📧 Email service endpoints will be available at:")
        print(f"   http://localhost:{port}/email/test-connection")
        print(f"   http://localhost:{port}/email/feedback")
        print()
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Run the main application
        from app.main import app
        app.run(host='0.0.0.0', port=int(port), debug=(flask_env == 'development'))
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()