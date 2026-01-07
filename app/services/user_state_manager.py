"""
User State Management Service
Handles comprehensive user data persistence including skills, target role, analysis, and roadmap progress
"""
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from app.db.firestore import FirestoreService

logger = logging.getLogger(__name__)

class UserStateManager:
    """Manages all user state data in Firestore"""
    
    def __init__(self):
        self.db_service = FirestoreService()
    
    def save_user_state(self, uid: str, state_data: Dict[str, Any]) -> bool:
        """
        Save comprehensive user state to Firestore
        
        Args:
            uid: User ID
            state_data: Dictionary containing user state data
                - skills: List of user skills
                - targetRole: Selected target role
                - analysis: Latest analysis data
                - roadmapProgress: Current roadmap progress
                - preferences: User preferences
        """
        try:
            # Prepare state document
            user_state = {
                'uid': uid,
                'lastUpdated': datetime.utcnow(),
                **state_data
            }
            
            # Save to user_state collection
            success = self.db_service.create_document('user_state', uid, user_state)
            if success:
                logger.info(f"Saved user state for {uid}")
                return True
            else:
                logger.error(f"Failed to save user state for {uid}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving user state for {uid}: {str(e)}")
            return False
    
    def get_user_state(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive user state from Firestore"""
        try:
            user_state = self.db_service.get_document('user_state', uid)
            if user_state:
                logger.info(f"Retrieved user state for {uid}")
                return user_state
            else:
                logger.info(f"No user state found for {uid}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user state for {uid}: {str(e)}")
            return None
    
    def update_user_skills(self, uid: str, skills: List[Dict]) -> bool:
        """Update user skills in state"""
        try:
            update_data = {
                'skills': skills,
                'lastUpdated': datetime.utcnow()
            }
            
            success = self.db_service.update_document('user_state', uid, update_data)
            if success:
                logger.info(f"Updated skills for user {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating skills for {uid}: {str(e)}")
            return False
    
    def update_target_role(self, uid: str, role_data: Dict) -> bool:
        """Update user's target role in state"""
        try:
            update_data = {
                'targetRole': role_data,
                'lastUpdated': datetime.utcnow()
            }
            
            success = self.db_service.update_document('user_state', uid, update_data)
            if success:
                logger.info(f"Updated target role for user {uid}: {role_data.get('title', 'Unknown')}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating target role for {uid}: {str(e)}")
            return False
    
    def update_analysis_data(self, uid: str, analysis_data: Dict) -> bool:
        """Update user's analysis data in state"""
        try:
            update_data = {
                'analysis': analysis_data,
                'analysisUpdatedAt': datetime.utcnow(),
                'lastUpdated': datetime.utcnow()
            }
            
            success = self.db_service.update_document('user_state', uid, update_data)
            if success:
                logger.info(f"Updated analysis data for user {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating analysis data for {uid}: {str(e)}")
            return False
    
    def update_roadmap_progress(self, uid: str, roadmap_data: Dict) -> bool:
        """Update user's roadmap progress in state"""
        try:
            update_data = {
                'roadmapProgress': roadmap_data,
                'roadmapUpdatedAt': datetime.utcnow(),
                'lastUpdated': datetime.utcnow()
            }
            
            success = self.db_service.update_document('user_state', uid, update_data)
            if success:
                logger.info(f"Updated roadmap progress for user {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating roadmap progress for {uid}: {str(e)}")
            return False
    
    def get_user_dashboard_data(self, uid: str) -> Dict[str, Any]:
        """Get all data needed for user dashboard"""
        try:
            user_state = self.get_user_state(uid)
            if not user_state:
                return {
                    'skills': [],
                    'targetRole': None,
                    'analysis': None,
                    'roadmapProgress': None,
                    'hasData': False
                }
            
            return {
                'skills': user_state.get('skills', []),
                'targetRole': user_state.get('targetRole'),
                'analysis': user_state.get('analysis'),
                'roadmapProgress': user_state.get('roadmapProgress'),
                'analysisUpdatedAt': user_state.get('analysisUpdatedAt'),
                'roadmapUpdatedAt': user_state.get('roadmapUpdatedAt'),
                'lastUpdated': user_state.get('lastUpdated'),
                'hasData': True
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data for {uid}: {str(e)}")
            return {
                'skills': [],
                'targetRole': None,
                'analysis': None,
                'roadmapProgress': None,
                'hasData': False
            }
    
    def initialize_user_state(self, uid: str) -> bool:
        """Initialize empty user state for new users"""
        try:
            initial_state = {
                'uid': uid,
                'skills': [],
                'targetRole': None,
                'analysis': None,
                'roadmapProgress': None,
                'preferences': {
                    'notifications': True,
                    'weeklyGoal': 10
                },
                'createdAt': datetime.utcnow(),
                'lastUpdated': datetime.utcnow()
            }
            
            success = self.db_service.create_document('user_state', uid, initial_state)
            if success:
                logger.info(f"Initialized user state for {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error initializing user state for {uid}: {str(e)}")
            return False
    
    def delete_user_state(self, uid: str) -> bool:
        """Delete user state (for account deletion)"""
        try:
            success = self.db_service.delete_document('user_state', uid)
            if success:
                logger.info(f"Deleted user state for {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting user state for {uid}: {str(e)}")
            return False