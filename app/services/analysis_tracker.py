"""
Analysis Progress Tracking Service
Tracks user's skill gap analysis over time and updates based on roadmap completion
"""
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from app.db.firestore import FirestoreService
from app.services.skills_engine import SkillsEngine

logger = logging.getLogger(__name__)

class AnalysisTracker:
    """Track and manage user's analysis progress over time"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        self.skills_engine = SkillsEngine()
    
    def create_initial_analysis(self, uid: str, role_id: str, analysis_data: Dict) -> str:
        """
        Create the initial analysis record when user first analyzes for a role
        """
        try:
            # Get user's current skills for baseline
            user_skills = self.skills_engine.get_user_skills(uid)
            
            analysis_record = {
                'uid': uid,
                'roleId': role_id,
                'initialAnalysis': analysis_data,
                'currentAnalysis': analysis_data,  # Same as initial at start
                'initialSkills': user_skills,
                'currentSkills': user_skills,  # Same as initial at start
                'createdAt': datetime.utcnow(),
                'lastUpdated': datetime.utcnow(),
                'roadmapCompletions': [],  # Track completed roadmap items
                'progressHistory': [{
                    'timestamp': datetime.utcnow(),
                    'readinessScore': analysis_data.get('readinessScore', 0),
                    'completedSkills': 0,
                    'event': 'initial_analysis'
                }],
                'isActive': True
            }
            
            # Check if analysis already exists for this role
            existing = self.db_service.query_collection(
                'user_analysis_history',
                [('uid', '==', uid), ('roleId', '==', role_id), ('isActive', '==', True)]
            )
            
            if existing:
                # Update existing analysis
                analysis_id = existing[0].get('id')
                if analysis_id:
                    success = self.db_service.update_document('user_analysis_history', analysis_id, analysis_record)
                    return analysis_id if success else None
            else:
                # Create new analysis record
                analysis_id = f"{uid}_{role_id}_{int(datetime.utcnow().timestamp())}"
                success = self.db_service.create_document('user_analysis_history', analysis_id, analysis_record)
                return analysis_id if success else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating initial analysis: {str(e)}")
            return None
    
    def update_analysis_on_completion(self, uid: str, role_id: str, completed_skill_id: str) -> bool:
        """
        Update analysis when user completes a roadmap item
        """
        try:
            # Get current analysis record
            analysis_records = self.db_service.query_collection(
                'user_analysis_history',
                [('uid', '==', uid), ('roleId', '==', role_id), ('isActive', '==', True)]
            )
            
            if not analysis_records:
                logger.warning(f"No analysis record found for user {uid} and role {role_id}")
                return False
            
            analysis_record = analysis_records[0]
            analysis_id = analysis_record.get('id')
            
            if not analysis_id:
                logger.error("Analysis record missing ID")
                return False
            
            # Get updated user skills
            current_skills = self.skills_engine.get_user_skills(uid)
            
            # Recalculate analysis with current skills
            updated_analysis = self._recalculate_analysis(role_id, current_skills)
            
            # Add completion to history
            roadmap_completions = analysis_record.get('roadmapCompletions', [])
            roadmap_completions.append({
                'skillId': completed_skill_id,
                'completedAt': datetime.utcnow()
            })
            
            # Add to progress history
            progress_history = analysis_record.get('progressHistory', [])
            progress_history.append({
                'timestamp': datetime.utcnow(),
                'readinessScore': updated_analysis.get('readinessScore', 0),
                'completedSkills': len(roadmap_completions),
                'event': 'skill_completed',
                'skillId': completed_skill_id
            })
            
            # Update the record
            update_data = {
                'currentAnalysis': updated_analysis,
                'currentSkills': current_skills,
                'roadmapCompletions': roadmap_completions,
                'progressHistory': progress_history,
                'lastUpdated': datetime.utcnow()
            }
            
            success = self.db_service.update_document('user_analysis_history', analysis_id, update_data)
            
            if success:
                logger.info(f"Updated analysis for user {uid}, role {role_id}, skill {completed_skill_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating analysis on completion: {str(e)}")
            return False
    
    def get_analysis_with_progress(self, uid: str, role_id: str) -> Optional[Dict]:
        """
        Get current analysis with progress comparison
        """
        try:
            analysis_records = self.db_service.query_collection(
                'user_analysis_history',
                [('uid', '==', uid), ('roleId', '==', role_id), ('isActive', '==', True)]
            )
            
            if not analysis_records:
                return None
            
            analysis_record = analysis_records[0]
            
            # Calculate progress metrics
            initial_analysis = analysis_record.get('initialAnalysis', {})
            current_analysis = analysis_record.get('currentAnalysis', {})
            progress_history = analysis_record.get('progressHistory', [])
            roadmap_completions = analysis_record.get('roadmapCompletions', [])
            
            initial_score = initial_analysis.get('readinessScore', 0)
            current_score = current_analysis.get('readinessScore', 0)
            score_improvement = current_score - initial_score
            
            # Calculate skills progress
            initial_matched = len(initial_analysis.get('matchedSkills', []))
            current_matched = len(current_analysis.get('matchedSkills', []))
            skills_improvement = current_matched - initial_matched
            
            return {
                'analysis': current_analysis,
                'progress': {
                    'initialScore': initial_score,
                    'currentScore': current_score,
                    'scoreImprovement': score_improvement,
                    'initialMatchedSkills': initial_matched,
                    'currentMatchedSkills': current_matched,
                    'skillsImprovement': skills_improvement,
                    'completedRoadmapItems': len(roadmap_completions),
                    'progressHistory': progress_history[-10:],  # Last 10 progress points
                    'lastUpdated': analysis_record.get('lastUpdated'),
                    'createdAt': analysis_record.get('createdAt')
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis with progress: {str(e)}")
            return None
    
    def _recalculate_analysis(self, role_id: str, user_skills: List[Dict]) -> Dict:
        """
        Recalculate skill gap analysis with current skills
        """
        try:
            # Get role requirements
            role_data = self.db_service.query_collection('job_roles', [('roleId', '==', role_id)])
            if not role_data:
                return {}
            
            role = role_data[0]
            required_skills = role.get('requiredSkills', [])
            
            # Perform analysis calculation
            matched_skills = []
            partial_skills = []
            missing_skills = []
            
            # Create user skills map
            user_skill_map = {skill['skillId']: skill for skill in user_skills}
            
            # Proficiency levels
            proficiency_values = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            
            for req_skill in required_skills:
                skill_id = req_skill['skillId']
                required_level = req_skill['minProficiency']
                required_value = proficiency_values.get(required_level, 2)
                
                if skill_id in user_skill_map:
                    user_skill = user_skill_map[skill_id]
                    user_level = user_skill.get('proficiency', 'beginner')
                    user_value = proficiency_values.get(user_level, 1)
                    
                    if user_value >= required_value:
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
                    # Get skill name from master skills
                    master_skills = self.db_service.query_collection('master_skills', [('skillId', '==', skill_id)])
                    skill_name = master_skills[0].get('name', skill_id) if master_skills else skill_id
                    
                    missing_skills.append({
                        'skillId': skill_id,
                        'skillName': skill_name,
                        'required': required_level
                    })
            
            # Calculate readiness score
            total_required = len(required_skills)
            fully_matched = len(matched_skills)
            partially_matched = len(partial_skills) * 0.5
            readiness_score = round(((fully_matched + partially_matched) / total_required) * 100) if total_required > 0 else 0
            
            return {
                'readinessScore': readiness_score,
                'matchedSkills': matched_skills,
                'partialSkills': partial_skills,
                'missingSkills': missing_skills
            }
            
        except Exception as e:
            logger.error(f"Error recalculating analysis: {str(e)}")
            return {}
    
    def get_user_analysis_history(self, uid: str, limit: int = 10) -> List[Dict]:
        """
        Get user's analysis history across all roles
        """
        try:
            records = self.db_service.query_collection(
                'user_analysis_history',
                [('uid', '==', uid)],
                order_by='lastUpdated',
                limit=limit
            )
            
            return records
            
        except Exception as e:
            logger.error(f"Error getting user analysis history: {str(e)}")
            return []