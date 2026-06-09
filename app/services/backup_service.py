import os
import json
import base64
import hashlib
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
import logging
from app.db.firestore import FirestoreService
from app.config import Config
from firebase_admin import firestore

logger = logging.getLogger(__name__)

# Constants
ADMIN_EMAIL = "akaashofficial21@gmail.com"
BACKUP_COLLECTION = "system_backups"
MAX_BACKUPS = 10
CHUNK_SIZE = 800000  # 800KB per chunk to comfortably fit within 1MB Firestore limit

class FirestoreJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Firestore-specific and non-standard types safely."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        # Handle Firestore DocumentReference
        if hasattr(obj, 'path') and hasattr(obj, 'id'):
            return {'__type__': 'DocumentReference', 'path': obj.path}
        # Handle bytes
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        try:
            return super().default(obj)
        except TypeError:
            # Resilient fallback to prevent failure
            return str(obj)

class BackupService:
    def __init__(self):
        self.db_service = FirestoreService()
        self.db = self.db_service.db
        
        # Derive a valid 32-byte url-safe base64 key for Fernet from the Flask SECRET_KEY
        secret = Config.SECRET_KEY
        if not secret:
            secret = os.environ.get('SECRET_KEY', 'default-fallback-secret-for-backup-1234')
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode('utf-8')).digest())
        self.fernet = Fernet(key)

    def _send_email(self, subject: str, html_body: str):
        """Sends an email notification."""
        try:
            smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('SMTP_PORT', 587))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASSWORD')

            if not smtp_user or not smtp_pass:
                logger.error("❌ Email credentials not found. Cannot send backup notification.")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"SkillBridge System <{smtp_user}>"
            msg['To'] = ADMIN_EMAIL

            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            logger.info(f"📧 Notification email sent to {ADMIN_EMAIL}: {subject}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email notification: {str(e)}")
            return False

    def perform_backup(self):
        """
        1. Fetches all data from Firestore.
        2. Encrypts the data securely.
        3. Chunks the encrypted string and saves to `system_backups`.
        4. Rotates old backups to keep exactly 10.
        5. Sends success or failure email.
        """
        start_time = datetime.now(timezone.utc)
        logger.info("🚀 Starting automated secure database backup...")
        
        try:
            # 0. Check for distributed lock (prevent multiple workers from backing up today)
            today_str = start_time.strftime("%Y-%m-%d")
            lock_ref = self.db.collection('system_metadata').document('backup_lock')
            lock_doc = lock_ref.get()
            
            if lock_doc.exists and lock_doc.to_dict().get('last_backup_date') == today_str:
                logger.info("✅ Backup already performed today by another process. Skipping.")
                return

            # Set lock immediately
            lock_ref.set({'last_backup_date': today_str, 'locked_at': start_time})

            # 1. Fetch all collections except the backup collection itself
            backup_data = {}
            collections = self.db.collections()
            doc_count = 0
            
            for collection in collections:
                if collection.id == BACKUP_COLLECTION:
                    continue  # Skip backing up the backups
                
                backup_data[collection.id] = {}
                for doc in collection.stream():
                    backup_data[collection.id][doc.id] = doc.to_dict()
                    doc_count += 1

            # 2. Serialize and Encrypt
            json_data = json.dumps(backup_data, cls=FirestoreJSONEncoder)
            encrypted_data = self.fernet.encrypt(json_data.encode('utf-8')).decode('utf-8')
            
            # 3. Store in Firestore (chunked)
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            backup_ref = self.db.collection(BACKUP_COLLECTION).document(timestamp)
            
            # Split encrypted string into chunks
            chunks = [encrypted_data[i:i + CHUNK_SIZE] for i in range(0, len(encrypted_data), CHUNK_SIZE)]
            
            # Save metadata
            backup_ref.set({
                'created_at': start_time,
                'total_chunks': len(chunks),
                'doc_count': doc_count,
                'status': 'completed'
            })
            
            # Save chunks in subcollection
            for i, chunk in enumerate(chunks):
                backup_ref.collection('chunks').document(f'chunk_{i}').set({'data': chunk})
                
            # 4. Enforce Queue (Keep max 10 backups)
            backup_docs = list(self.db.collection(BACKUP_COLLECTION).order_by('created_at', direction=firestore.Query.DESCENDING).stream())
            
            deleted_count = 0
            if len(backup_docs) > MAX_BACKUPS:
                docs_to_delete = backup_docs[MAX_BACKUPS:]
                for doc in docs_to_delete:
                    # Delete subcollection first
                    sub_chunks = doc.reference.collection('chunks').stream()
                    for sc in sub_chunks:
                        sc.reference.delete()
                    # Delete metadata doc
                    doc.reference.delete()
                    deleted_count += 1

            # 5. Send Success Email
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            html_body = f"""
            <h2>✅ SkillBridge Database Backup Successful</h2>
            <p>The automated secure backup has completed successfully.</p>
            <ul>
                <li><strong>Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
                <li><strong>Documents Backed Up:</strong> {doc_count}</li>
                <li><strong>Total Encrypted Chunks:</strong> {len(chunks)}</li>
                <li><strong>Duration:</strong> {duration:.2f} seconds</li>
                <li><strong>Backups Pruned:</strong> {deleted_count} (Maximum {MAX_BACKUPS} retained)</li>
            </ul>
            <p>Your data is securely encrypted with AES (Fernet) using your server's secret key and stored entirely within Firestore's <code>{BACKUP_COLLECTION}</code> collection.</p>
            """
            self._send_email("✅ SkillBridge Backup Completed", html_body)
            logger.info("✅ Automated backup completed successfully.")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ CRITICAL ERROR during automated backup: {error_msg}")
            
            html_body = f"""
            <h2 style="color: red;">🚨 CRITICAL: SkillBridge Database Backup Failed</h2>
            <p>An error occurred during the automated secure backup process, or a potential issue/crash was detected.</p>
            <p><strong>Error Details:</strong></p>
            <pre style="background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px;">{error_msg}</pre>
            <p><strong>Action Required:</strong> Please check your server logs immediately to ensure there are no data leakages or critical system crashes.</p>
            """
            self._send_email("🚨 URGENT: SkillBridge Backup Failed / Server Issue", html_body)

# Helper function to test encryption/decryption or perform manual restore if needed
def decrypt_backup_payload(encrypted_data: str, secret_key: str) -> dict:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode('utf-8')).digest())
    f = Fernet(key)
    decrypted_json = f.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
    return json.loads(decrypted_json)
