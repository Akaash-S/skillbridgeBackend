from google.cloud import firestore
from google.oauth2 import service_account
from typing import Dict, List, Optional, Any
import logging
import os
import json
import base64

logger = logging.getLogger(__name__)

# Global Firestore client
db = None
FIRESTORE_AVAILABLE = False

def init_firestore():
    """Initialize Firestore client with base64 credentials"""
    global db, FIRESTORE_AVAILABLE
    
    # Check if Firestore should be disabled
    if os.environ.get('DISABLE_FIREBASE', '').lower() in ('true', '1', 'yes'):
        logger.info("🔥 Firestore initialization disabled via DISABLE_FIREBASE environment variable")
        FIRESTORE_AVAILABLE = False
        return
    
    try:
        # Use base64 encoded service account
        firebase_base64 = os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')
        if not firebase_base64:
            logger.error("❌ FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable not found for Firestore")
            FIRESTORE_AVAILABLE = False
            return
        
        # Fix base64 padding if needed
        missing_padding = len(firebase_base64) % 4
        if missing_padding:
            firebase_base64 += '=' * (4 - missing_padding)
        
        # Decode base64 and parse JSON
        decoded_credentials = base64.b64decode(firebase_base64).decode('utf-8')
        service_account_info = json.loads(decoded_credentials)
        
        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        
        # Initialize Firestore with credentials
        db = firestore.Client(credentials=credentials, project=service_account_info.get('project_id'))
        
        logger.info("✅ Firestore client initialized successfully with base64 credentials")
        logger.info(f"🔥 Firestore Project ID: {service_account_info.get('project_id')}")
        FIRESTORE_AVAILABLE = True
        
    except json.JSONDecodeError as json_error:
        logger.error(f"❌ Invalid JSON in base64 credentials for Firestore: {str(json_error)}")
        FIRESTORE_AVAILABLE = False
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firestore: {str(e)}")
        FIRESTORE_AVAILABLE = False

def get_db():
    """Get Firestore client instance"""
    global db
    if db is None and FIRESTORE_AVAILABLE:
        init_firestore()
    return db

def is_firestore_available():
    """Check if Firestore is available and initialized"""
    return FIRESTORE_AVAILABLE

class FirestoreService:
    """Firestore database operations service with graceful fallback"""
    
    def __init__(self):
        if is_firestore_available():
            self.db = get_db()
        else:
            self.db = None
            # Only log once during initialization, not for every operation
            if not hasattr(FirestoreService, '_logged_unavailable'):
                logger.warning("⚠️ Firestore not available - using mock database operations")
                FirestoreService._logged_unavailable = True
    
    def _check_availability(self):
        """Check if Firestore is available (silent check)"""
        if not self.db:
            return False
        return True
    
    # Generic CRUD operations
    def create_document(self, collection: str, doc_id: str, data: Dict) -> bool:
        """Create a document in Firestore"""
        if not self._check_availability():
            return True  # Return success for development mode
            
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
        if not self._check_availability():
            return None  # Return None for development mode
            
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
        if not self._check_availability():
            return True  # Return success for development mode
            
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
        if not self._check_availability():
            return True  # Return success for development mode
            
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
        if not self._check_availability():
            return []  # Return empty list for development mode
            
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, operator, value in filters:
                    # Use the new filter keyword argument syntax
                    query = query.where(filter=firestore.FieldFilter(field, operator, value))
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            results = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id  # Add document ID to the data
                results.append(doc_data)
            return results
        except Exception as e:
            logger.error(f"Error querying collection {collection}: {str(e)}")
            return []
    
    def batch_write(self, operations: List[Dict]) -> bool:
        """Perform batch write operations"""
        if not self._check_availability():
            return True  # Return success for development mode
            
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
        if not self._check_availability():
            return True  # Return success for development mode
            
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