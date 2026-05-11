"""
Certificate Service
Handles roadmap completion verification and certificate issuance
"""
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import uuid
from app.db.firestore import FirestoreService
from app.services.user_state_manager import UserStateManager

logger = logging.getLogger(__name__)

class CertificateService:
    """Manages certificate issuance and verification"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        self.state_manager = UserStateManager()
    
    def verify_and_issue_certificate(self, uid: str, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Verifies if user has completed the roadmap for a role and issues a certificate
        
        Args:
            uid: User ID
            role_id: The role ID of the roadmap
            
        Returns:
            Certificate data if successful, None otherwise
        """
        try:
            # 1. Get active roadmap for this role
            roadmap = self.db_service.get_user_roadmap(uid)
            
            if not roadmap or roadmap.get('roleId') != role_id:
                logger.warning(f"No active roadmap found for user {uid} and role {role_id}")
                return None
            
            # 2. Check completion status
            milestones = roadmap.get('milestones', [])
            if not milestones:
                logger.warning(f"Roadmap for user {uid} has no milestones")
                return None
                
            total_skills = 0
            completed_skills = 0
            
            for milestone in milestones:
                skills = milestone.get('skills', [])
                for skill in skills:
                    total_skills += 1
                    if skill.get('completed', False):
                        completed_skills += 1
            
            # Check if 100% complete
            if total_skills == 0 or completed_skills < total_skills:
                logger.warning(f"Roadmap for user {uid} is not 100% complete: {completed_skills}/{total_skills}")
                return None
            
            # 3. Check if certificate already exists for this roadmap
            existing_certs = self.db_service.query_collection(
                'issued_certificates',
                [('uid', '==', uid), ('roleId', '==', role_id)]
            )
            
            if existing_certs:
                logger.info(f"Certificate already exists for user {uid} and role {role_id}")
                return existing_certs[0]
            
            # 4. Fetch user name from user profile/state
            user_state = self.state_manager.get_user_state(uid)
            user_name = "SkillBridge User"
            if user_state and user_state.get('name'):
                user_name = user_state.get('name')
            
            # Get role title
            role_title = role_id.replace('-', ' ').title()
            # Try to get from roadmap if stored
            if roadmap.get('roleTitle'):
                role_title = roadmap.get('roleTitle')
            
            # 5. Generate Certificate
            cert_id = f"SB-{uuid.uuid4().hex[:12].upper()}"
            completion_date = datetime.utcnow()
            
            certificate_data = {
                'certificateId': cert_id,
                'uid': uid,
                'userName': user_name,
                'roleId': role_id,
                'roleName': role_title,
                'completionDate': completion_date,
                'issuedAt': completion_date,
                'totalSkills': total_skills,
                'roadmapId': roadmap.get('id', ''),
                'status': 'verified'
            }
            
            # 6. Save to Firestore
            success = self.db_service.create_document('issued_certificates', cert_id, certificate_data)
            
            if success:
                logger.info(f"✅ Issued certificate {cert_id} for user {uid}")
                
                # Log activity
                self.db_service.log_user_activity(
                    uid, 
                    'CERTIFICATE_ISSUED', 
                    f'Earned certificate for {role_title}'
                )
                
                return certificate_data
            else:
                logger.error(f"❌ Failed to save certificate {cert_id} for user {uid}")
                return None
                
        except Exception as e:
            logger.error(f"Error issuing certificate for user {uid}: {str(e)}")
            return None
            
    def get_user_certificates(self, uid: str) -> List[Dict[str, Any]]:
        """Fetch all certificates issued to a user"""
        try:
            return self.db_service.query_collection('issued_certificates', [('uid', '==', uid)])
        except Exception as e:
            logger.error(f"Error fetching certificates for user {uid}: {str(e)}")
            return []
            
    def get_certificate_by_id(self, cert_id: str) -> Optional[Dict[str, Any]]:
        """Verify a certificate by its ID"""
        try:
            return self.db_service.get_document('issued_certificates', cert_id)
        except Exception as e:
            logger.error(f"Error fetching certificate {cert_id}: {str(e)}")
            return None
