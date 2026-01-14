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
            
            # Use create_if_missing=True to handle new users
            success = self.db_service.update_document('user_state', uid, update_data, create_if_missing=True)
            if success:
                logger.info(f"Updated skills for user {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating skills for {uid}: {str(e)}")
            return False
    
    def update_target_role(self, uid: str, role_data: Dict) -> bool:
        """Update user's target role in state"""
        try:
            logger.info(f"🎯 UserStateManager: Updating target role for {uid}")
            logger.info(f"📋 Role data: {role_data}")
            
            update_data = {
                'targetRole': role_data,
                'lastUpdated': datetime.utcnow()
            }
            
            logger.info(f"🔄 Calling db_service.update_document with data: {update_data}")
            # Use create_if_missing=True to handle new users
            success = self.db_service.update_document('user_state', uid, update_data, create_if_missing=True)
            
            if success:
                logger.info(f"✅ Target role updated successfully in database for user {uid}: {role_data.get('title', 'Unknown')}")
            else:
                logger.error(f"❌ Database update failed for user {uid}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Exception in update_target_role for {uid}: {str(e)}")
            return False
    
    def update_analysis_data(self, uid: str, analysis_data: Dict) -> bool:
        """Update user's analysis data in state"""
        try:
            update_data = {
                'analysis': analysis_data,
                'analysisUpdatedAt': datetime.utcnow(),
                'lastUpdated': datetime.utcnow()
            }
            
            # Use create_if_missing=True to handle new users
            success = self.db_service.update_document('user_state', uid, update_data, create_if_missing=True)
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
            
            # Use create_if_missing=True to handle new users
            success = self.db_service.update_document('user_state', uid, update_data, create_if_missing=True)
            if success:
                logger.info(f"Updated roadmap progress for user {uid}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating roadmap progress for {uid}: {str(e)}")
            return False
    
    def get_optimized_dashboard_data(self, uid: str) -> Dict[str, Any]:
        """Get optimized dashboard data with skill-role matching"""
        try:
            # Get user state and skills in parallel
            user_state = self.get_user_state(uid)
            user_skills = self.db_service.get_user_skills(uid)
            
            if not user_state:
                return {
                    'skills': [],
                    'skillsCount': 0,
                    'targetRole': None,
                    'analysis': None,
                    'roadmapProgress': None,
                    'skillGapSummary': None,
                    'hasData': False
                }
            
            target_role = user_state.get('targetRole')
            analysis = user_state.get('analysis')
            roadmap_progress = user_state.get('roadmapProgress')
            
            # Calculate skill gap summary if we have a target role
            skill_gap_summary = None
            if target_role and user_skills:
                skill_gap_summary = self._calculate_skill_gap_summary(user_skills, target_role)
            
            # Calculate dashboard metrics
            skills_count = len(user_skills)
            roadmap_completion = 0
            if roadmap_progress:
                total_items = roadmap_progress.get('totalItems', 0)
                completed_items = roadmap_progress.get('completedItems', 0)
                roadmap_completion = (completed_items / total_items * 100) if total_items > 0 else 0
            
            return {
                'skills': user_skills[:10],  # Limit to 10 for dashboard
                'skillsCount': skills_count,
                'targetRole': target_role,
                'analysis': analysis,
                'roadmapProgress': roadmap_progress,
                'roadmapCompletion': round(roadmap_completion, 1),
                'skillGapSummary': skill_gap_summary,
                'analysisUpdatedAt': user_state.get('analysisUpdatedAt'),
                'roadmapUpdatedAt': user_state.get('roadmapUpdatedAt'),
                'lastUpdated': user_state.get('lastUpdated'),
                'hasData': True
            }
            
        except Exception as e:
            logger.error(f"Error getting optimized dashboard data for {uid}: {str(e)}")
            return {
                'skills': [],
                'skillsCount': 0,
                'targetRole': None,
                'analysis': None,
                'roadmapProgress': None,
                'skillGapSummary': None,
                'hasData': False
            }
    
    def get_initial_load_data(self, uid: str) -> Dict[str, Any]:
        """Get all initial data needed for the application in one optimized request"""
        try:
            # Get user state
            user_state = self.get_user_state(uid) or {}
            
            # Get user skills directly from database (not from user state)
            user_skills = self.db_service.get_user_skills(uid)
            
            # Get master skills (cached)
            master_skills = self.db_service.query_collection('skills_master', [])
            
            # Get job roles (cached)
            job_roles = self.db_service.query_collection('job_roles', [])
            
            # Format skills for frontend
            formatted_user_skills = []
            for skill in user_skills:
                # Find master skill details
                master_skill = next((s for s in master_skills if s.get('skillId') == skill.get('skillId')), None)
                if master_skill:
                    formatted_skill = {
                        'id': skill.get('skillId'),
                        'name': master_skill.get('name'),
                        'category': master_skill.get('category'),
                        'proficiency': skill.get('level', 'beginner')
                    }
                    formatted_user_skills.append(formatted_skill)
            
            # Format master skills for frontend
            formatted_master_skills = []
            for skill in master_skills:
                formatted_skill = {
                    'id': skill.get('skillId'),
                    'name': skill.get('name'),
                    'category': skill.get('category')
                }
                formatted_master_skills.append(formatted_skill)
            
            # Format job roles for frontend
            formatted_job_roles = []
            for role in job_roles:
                formatted_role = {
                    'id': role.get('roleId'),
                    'title': role.get('title'),
                    'description': role.get('description'),
                    'requiredSkills': role.get('requiredSkills', []),
                    'category': role.get('category'),
                    'avgSalary': role.get('avgSalary'),
                    'demand': role.get('demand')
                }
                formatted_job_roles.append(formatted_role)
            
            # Get target role analysis if available
            target_role = user_state.get('targetRole')
            skill_gap_analysis = None
            if target_role and formatted_user_skills:
                skill_gap_analysis = self._perform_skill_gap_analysis(formatted_user_skills, target_role)
            
            # Sync user state with actual database data
            if formatted_user_skills or target_role:
                # Update user state to ensure it's in sync with database
                updated_state = {
                    'skills': formatted_user_skills,
                    'targetRole': target_role,
                    'analysis': skill_gap_analysis,
                    'lastSynced': datetime.utcnow()
                }
                
                # Merge with existing state
                if user_state:
                    user_state.update(updated_state)
                else:
                    user_state = updated_state
                
                # Save updated state back to database
                self.save_user_state(uid, user_state)
            
            return {
                'userState': user_state,
                'userSkills': formatted_user_skills,
                'masterSkills': formatted_master_skills,
                'jobRoles': formatted_job_roles,
                'skillGapAnalysis': skill_gap_analysis,
                'hasData': len(formatted_user_skills) > 0 or target_role is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting initial load data for {uid}: {str(e)}")
            return {
                'userState': {},
                'userSkills': [],
                'masterSkills': [],
                'jobRoles': [],
                'skillGapAnalysis': None,
                'hasData': False
            }
    
    def _calculate_skill_gap_summary(self, user_skills: List[Dict], target_role: Dict) -> Dict[str, Any]:
        """Calculate a quick skill gap summary for dashboard"""
        try:
            required_skills = target_role.get('requiredSkills', [])
            if not required_skills:
                return None
            
            user_skill_map = {skill.get('skillId'): skill.get('level', 'beginner') for skill in user_skills}
            
            matched_count = 0
            partial_count = 0
            missing_count = 0
            
            proficiency_values = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            
            for req_skill in required_skills:
                skill_id = req_skill.get('skillId')
                required_level = req_skill.get('minProficiency', 'intermediate')
                
                if skill_id in user_skill_map:
                    user_level = user_skill_map[skill_id]
                    if proficiency_values.get(user_level, 1) >= proficiency_values.get(required_level, 2):
                        matched_count += 1
                    else:
                        partial_count += 1
                else:
                    missing_count += 1
            
            total_required = len(required_skills)
            readiness_score = ((matched_count + partial_count * 0.5) / total_required * 100) if total_required > 0 else 0
            
            return {
                'totalRequired': total_required,
                'matched': matched_count,
                'partial': partial_count,
                'missing': missing_count,
                'readinessScore': round(readiness_score, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating skill gap summary: {str(e)}")
            return None
    
    def _perform_skill_gap_analysis(self, user_skills: List[Dict], target_role: Dict) -> Dict[str, Any]:
        """Perform detailed skill gap analysis"""
        try:
            required_skills = target_role.get('requiredSkills', [])
            if not required_skills:
                return None
            
            user_skill_map = {skill.get('id'): skill for skill in user_skills}
            
            matched_skills = []
            partial_skills = []
            missing_skills = []
            
            proficiency_values = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            
            for req_skill in required_skills:
                skill_id = req_skill.get('skillId')
                required_level = req_skill.get('minProficiency', 'intermediate')
                
                if skill_id in user_skill_map:
                    user_skill = user_skill_map[skill_id]
                    user_level = user_skill.get('proficiency', 'beginner')
                    
                    if proficiency_values.get(user_level, 1) >= proficiency_values.get(required_level, 2):
                        matched_skills.append({
                            'skill': user_skill,
                            'required': required_level
                        })
                    else:
                        partial_skills.append({
                            'skill': user_skill,
                            'required': required_level
                        })
                else:
                    missing_skills.append({
                        'skillId': skill_id,
                        'skillName': skill_id.replace('-', ' ').title(),  # Basic formatting
                        'required': required_level
                    })
            
            total_required = len(required_skills)
            readiness_score = ((len(matched_skills) + len(partial_skills) * 0.5) / total_required * 100) if total_required > 0 else 0
            
            return {
                'readinessScore': round(readiness_score, 1),
                'matchedSkills': matched_skills,
                'partialSkills': partial_skills,
                'missingSkills': missing_skills
            }
            
        except Exception as e:
            logger.error(f"Error performing skill gap analysis: {str(e)}")
            return None
    
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
    
    def sync_user_state_with_database(self, uid: str) -> bool:
        """Sync user state with actual database data"""
        try:
            # Get actual data from database
            user_skills = self.db_service.get_user_skills(uid)
            master_skills = self.db_service.query_collection('skills_master', [])
            
            # Format user skills
            formatted_user_skills = []
            for skill in user_skills:
                master_skill = next((s for s in master_skills if s.get('skillId') == skill.get('skillId')), None)
                if master_skill:
                    formatted_skill = {
                        'id': skill.get('skillId'),
                        'name': master_skill.get('name'),
                        'category': master_skill.get('category'),
                        'proficiency': skill.get('level', 'beginner')
                    }
                    formatted_user_skills.append(formatted_skill)
            
            # Get current user state
            current_state = self.get_user_state(uid) or {}
            
            # Update state with database data
            updated_state = {
                **current_state,
                'skills': formatted_user_skills,
                'lastSynced': datetime.utcnow(),
                'lastUpdated': datetime.utcnow()
            }
            
            # Save updated state
            return self.save_user_state(uid, updated_state)
            
        except Exception as e:
            logger.error(f"Error syncing user state for {uid}: {str(e)}")
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