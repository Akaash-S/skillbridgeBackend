import os
import sys

# Ensure python path includes the current backend directory so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    print("=" * 60)
    print("  SKILLBRIDGE LEARNING RESOURCES CLEANUP  ")
    print("=" * 60)
    
    # Initialize Firestore Service
    from app.db.firestore import FirestoreService, init_firestore, is_firestore_available
    
    init_firestore()
    
    if not is_firestore_available():
        print("[Error] Firestore is not initialized/available. Check environment variables.")
        sys.exit(1)
        
    db_service = FirestoreService()
    
    print("[Info] Querying learning_resources collection...")
    try:
        # Get all resources of type 'video'
        resources = db_service.query_collection('learning_resources', [('type', '==', 'video')])
        print(f"[Info] Found {len(resources)} total cached video resources.")
        
        # Filter resources with duration '20m'
        to_delete = []
        for res in resources:
            r_id = res.get('id')
            duration = res.get('duration')
            url = res.get('url', '')
            
            # Check if it has a hardcoded duration of '20m' and is a YouTube/video link
            if duration == '20m' and r_id and (r_id.startswith('yt_') or 'youtube.com' in url or 'youtu.be' in url):
                to_delete.append(r_id)
                
        print(f"[Info] Found {len(to_delete)} video resources with static '20m' duration to delete.")
        
        deleted_count = 0
        for r_id in to_delete:
            success = db_service.delete_document('learning_resources', r_id)
            if success:
                deleted_count += 1
                
        print(f"[Success] Cleanup finished. Successfully deleted {deleted_count} out of {len(to_delete)} resources.")
        
    except Exception as e:
        print(f"[Error] Error performing cleanup: {str(e)}")

if __name__ == "__main__":
    main()
