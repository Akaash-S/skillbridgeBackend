from google.cloud import firestore
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Global Firestore client
db = None

def init_firestore():
    """Initialize Firestore client"""
    global db
    try:
        db = firestore.Client()
        logger.info("Firestore client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {str(e)}")
        raise

def get_db():
    """Get Firestore client instance"""
    global db
    if db is None:
        init_firestore()
    return db

class FirestoreService:
    """Firestore database operations service"""
    
    def __init__(self):
        self.db = get_db()
    
    # Generic CRUD operations
    def create_document(self, collection: str, doc_id: str, data: Dict) -> bool:
        """Create a document in Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(data)
            logger.info(f"Document created: {collection}/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating document {collection}/{doc_id}: {str(e)}")
            return False
    
    def get_document(self, collection: str, doc_id: str) -> Optional[Dict]:
        """Get a document from Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting document {collection}/{doc_id}: {str(e)}")
            return None
    
    def update_document(self, collection: str, doc_id: str, data: Dict) -> bool:
        """Update a document in Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.update(data)
            logger.info(f"Document updated: {collection}/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating document {collection}/{doc_id}: {str(e)}")
            return False
    
    def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.delete()
            logger.info(f"Document deleted: {collection}/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {collection}/{doc_id}: {str(e)}")
            return False
    
    def query_collection(self, collection: str, filters: List = None, limit: int = None) -> List[Dict]:
        """Query a collection with optional filters"""
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error querying collection {collection}: {str(e)}")
            return []
    
    def batch_write(self, operations: List[Dict]) -> bool:
        """Perform batch write operations"""
        try:
            batch = self.db.batch()
            
            for op in operations:
                doc_ref = self.db.collection(op['collection']).document(op['doc_id'])
                
                if op['operation'] == 'set':
                    batch.set(doc_ref, op['data'])
                elif op['operation'] == 'update':
                    batch.update(doc_ref, op['data'])
                elif op['operation'] == 'delete':
                    batch.delete(doc_ref)
            
            batch.commit()
            logger.info(f"Batch write completed: {len(operations)} operations")
            return True
        except Exception as e:
            logger.error(f"Error in batch write: {str(e)}")
            return False
    
    # User-specific operations
    def get_user_skills(self, uid: str) -> List[Dict]:
        """Get all skills for a user"""
        return self.query_collection('user_skills', [('uid', '==', uid)])
    
    def get_user_roadmap(self, uid: str) -> Optional[Dict]:
        """Get active roadmap for a user"""
        roadmaps = self.query_collection('user_roadmaps', [
            ('uid', '==', uid),
            ('isActive', '==', True)
        ], limit=1)
        return roadmaps[0] if roadmaps else None
    
    def get_user_activity(self, uid: str, limit: int = 50) -> List[Dict]:
        """Get recent activity for a user"""
        return self.query_collection('activity_logs', [('uid', '==', uid)], limit=limit)
    
    def log_user_activity(self, uid: str, activity_type: str, message: str) -> bool:
        """Log user activity"""
        from datetime import datetime
        
        activity_data = {
            'uid': uid,
            'type': activity_type,
            'message': message,
            'createdAt': datetime.utcnow()
        }
        
        # Generate unique ID for activity log
        doc_ref = self.db.collection('activity_logs').document()
        return self.create_document('activity_logs', doc_ref.id, activity_data)