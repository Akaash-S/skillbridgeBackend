#!/usr/bin/env python3
"""
SkillBridge Suite Backend Runner
Simple script to run the Flask application
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from app import create_app

def main():
    """Main function to run the Flask app"""
    try:
        # Create Flask app
        app = create_app()
        
        # Get configuration
        port = int(os.environ.get('PORT', 8000))
        debug = os.environ.get('FLASK_ENV') == 'development'
        host = '0.0.0.0'
        
        print(f"🚀 Starting SkillBridge Suite Backend...")
        print(f"📍 Server: http://{host}:{port}")
        print(f"🔧 Environment: {'Development' if debug else 'Production'}")
        print(f"📊 Health Check: http://{host}:{port}/health")
        print("=" * 50)
        
        # Run the Flask app
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        print(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()