import pyotp
import qrcode
import io
import base64
import secrets
import string
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import logging

logger = logging.getLogger(__name__)

class MFAService:
    def __init__(self):
        self.issuer_name = os.getenv('MFA_ISSUER_NAME', 'SkillBridge')
        self.secret_key = os.getenv('MFA_SECRET_KEY', 'default-secret-key-change-in-production')
        self._cipher_suite = self._get_cipher_suite()
    
    def _get_cipher_suite(self):
        """Create cipher suite for encrypting/decrypting MFA secrets"""
        # Derive key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'skillbridge_mfa_salt',  # In production, use a random salt per user
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        return Fernet(key)
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret for a user"""
        return pyotp.random_base32()
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt the TOTP secret for storage"""
        try:
            encrypted = self._cipher_suite.encrypt(secret.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt MFA secret: {str(e)}")
            raise
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt the TOTP secret for verification"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_secret.encode())
            decrypted = self._cipher_suite.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt MFA secret: {str(e)}")
            raise
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """Generate QR code for Google Authenticator setup"""
        try:
            # Create TOTP URI
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_email,
                issuer_name=self.issuer_name
            )
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 string
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{qr_code_base64}"
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {str(e)}")
            raise
    
    def verify_totp_code(self, secret: str, code: str, window: int = 1) -> bool:
        """Verify TOTP code from authenticator app"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
        except Exception as e:
            logger.error(f"Failed to verify TOTP code: {str(e)}")
            return False
    
    def generate_recovery_codes(self, count: int = 10) -> list:
        """Generate recovery codes for account recovery"""
        recovery_codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            # Format as XXXX-XXXX for better readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            recovery_codes.append(formatted_code)
        
        return recovery_codes
    
    def hash_recovery_code(self, code: str) -> str:
        """Hash recovery code for secure storage"""
        # Remove formatting and convert to uppercase
        clean_code = code.replace('-', '').upper()
        
        # Use PBKDF2 for hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'skillbridge_recovery_salt',
            iterations=100000,
        )
        hashed = kdf.derive(clean_code.encode())
        return base64.urlsafe_b64encode(hashed).decode()
    
    def verify_recovery_code(self, code: str, hashed_code: str) -> bool:
        """Verify recovery code against stored hash"""
        try:
            return self.hash_recovery_code(code) == hashed_code
        except Exception as e:
            logger.error(f"Failed to verify recovery code: {str(e)}")
            return False
    
    def is_setup_required(self, user_mfa_data: dict) -> bool:
        """Check if MFA setup is required for user"""
        return not user_mfa_data or not user_mfa_data.get('enabled', False)
    
    def get_backup_codes_count(self, user_mfa_data: dict) -> int:
        """Get count of unused recovery codes"""
        if not user_mfa_data or not user_mfa_data.get('recovery_codes'):
            return 0
        
        unused_codes = [code for code in user_mfa_data['recovery_codes'] if not code.get('used', False)]
        return len(unused_codes)
    
    def mark_recovery_code_used(self, user_mfa_data: dict, code: str) -> dict:
        """Mark a recovery code as used"""
        if not user_mfa_data or not user_mfa_data.get('recovery_codes'):
            return user_mfa_data
        
        code_hash = self.hash_recovery_code(code)
        
        for recovery_code in user_mfa_data['recovery_codes']:
            if recovery_code['hash'] == code_hash:
                recovery_code['used'] = True
                recovery_code['used_at'] = datetime.utcnow().isoformat()
                break
        
        return user_mfa_data
    
    def create_mfa_session(self, user_id: str) -> str:
        """Create temporary MFA session token"""
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # In a real implementation, you'd store this in Redis or database with expiration
        # For now, we'll include timestamp in the token for validation
        timestamp = datetime.utcnow().timestamp()
        session_data = f"{user_id}:{timestamp}:{session_token}"
        
        # Encrypt session data
        encrypted_session = self._cipher_suite.encrypt(session_data.encode())
        return base64.urlsafe_b64encode(encrypted_session).decode()
    
    def verify_mfa_session(self, session_token: str, max_age_minutes: int = 10) -> str:
        """Verify MFA session token and return user ID"""
        try:
            # Decrypt session data
            encrypted_bytes = base64.urlsafe_b64decode(session_token.encode())
            decrypted = self._cipher_suite.decrypt(encrypted_bytes)
            session_data = decrypted.decode()
            
            # Parse session data
            parts = session_data.split(':')
            if len(parts) != 3:
                return None
            
            user_id, timestamp_str, _ = parts
            timestamp = float(timestamp_str)
            
            # Check if session is still valid
            session_age = datetime.utcnow().timestamp() - timestamp
            if session_age > (max_age_minutes * 60):
                return None
            
            return user_id
            
        except Exception as e:
            logger.error(f"Failed to verify MFA session: {str(e)}")
            return None

# Global MFA service instance
mfa_service = MFAService()