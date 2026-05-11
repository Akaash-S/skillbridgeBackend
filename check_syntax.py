import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Checking app initialization...")
    from app import create_app
    app = create_app()
    print("SUCCESS: App initialized successfully (Syntax and Imports OK)")
except Exception as e:
    print(f"ERROR: Initialization failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
