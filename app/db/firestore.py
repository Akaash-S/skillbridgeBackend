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
    if db is None and FIRESTORE_AVAILABLE:
        init_firestore()
    return db

def is_firestore_available():
    """Check if Firestore is available and initialized"""
    return FIRESTORE_AVAILABLE

def is_mock_allowed() -> bool:
    """Check if mock database operations are explicitly permitted for local development."""
    return os.environ.get('ALLOW_MOCK_DB', '').lower() in ('true', '1', 'yes') or \
           os.environ.get('MOCK_FIRESTORE', '').lower() in ('true', '1', 'yes')

class FirestoreService:
    """Firestore database operations service with fail-closed production semantics"""
    
    def __init__(self):
        if is_firestore_available():
            self.db = get_db()
        else:
            self.db = None
            if not hasattr(FirestoreService, '_logged_unavailable'):
                if is_mock_allowed():
                    logger.warning("⚠️ Firestore not available - ALLOW_MOCK_DB is active, using mock operations for local dev")
                else:
                    logger.error("🚨 CRITICAL: Firestore is unavailable and ALLOW_MOCK_DB is not set. All database operations will fail closed!")
                FirestoreService._logged_unavailable = True
    
    def _check_availability(self):
        """Check if Firestore is available (silent check)"""
        if not self.db:
            return False
        return True
    
    # Generic CRUD operations
    def create_document(self, collection: str, doc_id: str, data: Dict) -> bool:
        """Create a document in Firestore (fails closed if unavailable unless mock allowed)"""
        if not self._check_availability():
            if is_mock_allowed():
                logger.warning(f"⚠️ Mock Firestore create allowed for local dev: {collection}/{doc_id}")
                return True
            logger.error(f"❌ Firestore unavailable. Rejecting create_document for {collection}/{doc_id} (fail closed).")
            return False
            
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
    
    def update_document(self, collection: str, doc_id: str, data: Dict, create_if_missing: bool = False) -> bool:
        """Update a document in Firestore (fails closed if unavailable unless mock allowed)"""
        logger.info(f"🔥 FirestoreService: Attempting to update document {collection}/{doc_id}")
        
        if not self._check_availability():
            if is_mock_allowed():
                logger.warning(f"⚠️ Mock Firestore update allowed: {collection}/{doc_id}")
                return True
            logger.error(f"❌ Firestore unavailable. Rejecting update_document for {collection}/{doc_id} (fail closed).")
            return False
            
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            
            if create_if_missing:
                # Use set with merge=True to create document if it doesn't exist
                doc_ref.set(data, merge=True)
                logger.info(f"✅ Document set with merge: {collection}/{doc_id}")
            else:
                # Use update (requires document to exist)
                doc_ref.update(data)
                logger.info(f"✅ Document updated: {collection}/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating document {collection}/{doc_id}: {str(e)}")
            # If update fails because document doesn't exist, try creating it
            if "No document to update" in str(e) or "NOT_FOUND" in str(e):
                try:
                    logger.info(f"🔄 Document doesn't exist, creating new document: {collection}/{doc_id}")
                    doc_ref.set(data, merge=True)
                    logger.info(f"✅ Document created with merge: {collection}/{doc_id}")
                    return True
                except Exception as create_error:
                    logger.error(f"❌ Error creating document {collection}/{doc_id}: {str(create_error)}")
                    return False
            return False
    
    def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from Firestore (fails closed if unavailable unless mock allowed)"""
        if not self._check_availability():
            if is_mock_allowed():
                logger.warning(f"⚠️ Mock Firestore delete allowed: {collection}/{doc_id}")
                return True
            logger.error(f"❌ Firestore unavailable. Rejecting delete_document for {collection}/{doc_id} (fail closed).")
            return False
            
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
            if not is_mock_allowed():
                logger.error(f"❌ Firestore unavailable. Cannot query collection {collection} (fail closed).")
            return []
            
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
        """Perform batch write operations (fails closed if unavailable unless mock allowed)"""
        if not self._check_availability():
            if is_mock_allowed():
                logger.warning(f"⚠️ Mock Firestore batch_write allowed ({len(operations)} operations)")
                return True
            logger.error("❌ Firestore unavailable. Rejecting batch_write (fail closed).")
            return False
            
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
        """Log user activity (fails closed if unavailable unless mock allowed)"""
        if not self._check_availability():
            if is_mock_allowed():
                return True
            logger.error(f"❌ Firestore unavailable. Failed to log activity for {uid} (fail closed).")
            return False
            
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