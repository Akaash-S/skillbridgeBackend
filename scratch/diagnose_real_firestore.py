import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / '.env')

from app.db.firestore import init_firestore, is_firestore_available, FirestoreService

def main():
    print("🚀 Initializing Firestore...")
    init_firestore()
    
    if not is_firestore_available():
        print("❌ Firestore could not be initialized!")
        return
        
    print("✅ Firestore connected successfully!")
    db_service = FirestoreService()
    
    # Check collections
    for col in ['skills_master', 'job_roles', 'learning_resources', 'users', 'user_skills', 'user_roadmaps', 'roadmap_templates', 'system_backups', 'system_logs', 'activity_logs', 'system_notifications']:
        try:
            res = db_service.query_collection(col)
            print(f"📦 Collection '{col}': {len(res)} documents")
            if res:
                print(f"   Sample keys from first document: {list(res[0].keys())[:5]}")
        except Exception as e:
            print(f"❌ Error querying '{col}': {e}")

if __name__ == '__main__':
    main()
