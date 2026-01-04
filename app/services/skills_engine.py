from app.db.firestore import FirestoreService
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SkillsEngine:
    """Core skills management and analysis engine"""
    
    def __init__(self):
        self.db_service = FirestoreService()
    
    def get_master_skills(self, category: str = None, skill_type: str = None) -> List[Dict]:
        """Get skills from master catalog with optional filtering"""
        try:
            filters = []
            
            if category:
                filters.append(('category', '==', category))
            
            if skill_type:
                filters.append(('type', '==', skill_type))
            
            skills = self.db_service.query_collection('skills_master', filters)
            return skills
            
        except Exception as e:
            logger.error(f"Error getting master skills: {str(e)}")
            return []
    
    def search_skills(self, query: str, limit: int = 20) -> List[Dict]:
        """Search skills by name or aliases"""
        try:
            # Get all skills (Firestore doesn't support full-text search natively)
            all_skills = self.get_master_skills()
            
            query_lower = query.lower()
            matching_skills = []
            
            for skill in all_skills:
                # Check skill name
                if query_lower in skill.get('name', '').lower():
                    matching_skills.append(skill)
                    continue
                
                # Check aliases
                aliases = skill.get('aliases', [])
                if any(query_lower in alias.lower() for alias in aliases):
                    matching_skills.append(skill)
            
            return matching_skills[:limit]
            
        except Exception as e:
            logger.error(f"Error searching skills: {str(e)}")
            return []
    
    def get_user_skills(self, uid: str) -> List[Dict]:
        """Get all skills for a user with master skill details"""
        try:
            user_skills = self.db_service.get_user_skills(uid)
            
            # Enrich with master skill data
            enriched_skills = []
            for user_skill in user_skills:
                skill_id = user_skill.get('skillId')
                master_skill = self.db_service.get_document('skills_master', skill_id)
                
                if master_skill:
                    enriched_skill = {
                        **master_skill,
                        'userLevel': user_skill.get('level'),
                        'userConfidence': user_skill.get('confidence'),
                        'source': user_skill.get('source'),
                        'lastUpdatedAt': user_skill.get('lastUpdatedAt')
                    }
                    enriched_skills.append(enriched_skill)
            
            return enriched_skills
            
        except Exception as e:
            logger.error(f"Error getting user skills: {str(e)}")
            return []
    
    def add_user_skill(self, uid: str, skill_id: str, level: str, confidence: str = 'medium') -> bool:
        """Add or update a skill for a user"""
        try:
            # Validate skill exists in master catalog
            master_skill = self.db_service.get_document('skills_master', skill_id)
            if not master_skill:
                logger.warning(f"Skill not found in master catalog: {skill_id}")
                return False
            
            # Validate level
            valid_levels = master_skill.get('levels', ['beginner', 'intermediate', 'advanced'])
            if level not in valid_levels:
                logger.warning(f"Invalid level {level} for skill {skill_id}")
                return False
            
            # Create composite key for user_skills
            user_skill_id = f"{uid}_{skill_id}"
            
            user_skill_data = {
                'uid': uid,
                'skillId': skill_id,
                'level': level,
                'confidence': confidence,
                'source': 'self-reported',
                'lastUpdatedAt': datetime.utcnow()
            }
            
            success = self.db_service.create_document('user_skills', user_skill_id, user_skill_data)
            
            if success:
                # Log activity
                skill_name = master_skill.get('name', skill_id)
                self.db_service.log_user_activity(
                    uid, 
                    'SKILL_ADDED', 
                    f'Added skill: {skill_name} ({level})'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding user skill: {str(e)}")
            return False
    
    def update_user_skill(self, uid: str, skill_id: str, level: str = None, confidence: str = None) -> bool:
        """Update a user's skill level or confidence"""
        try:
            user_skill_id = f"{uid}_{skill_id}"
            
            # Check if user skill exists
            existing_skill = self.db_service.get_document('user_skills', user_skill_id)
            if not existing_skill:
                logger.warning(f"User skill not found: {user_skill_id}")
                return False
            
            # Prepare update data
            update_data = {'lastUpdatedAt': datetime.utcnow()}
            
            if level:
                # Validate level against master skill
                master_skill = self.db_service.get_document('skills_master', skill_id)
                if master_skill:
                    valid_levels = master_skill.get('levels', ['beginner', 'intermediate', 'advanced'])
                    if level not in valid_levels:
                        logger.warning(f"Invalid level {level} for skill {skill_id}")
                        return False
                update_data['level'] = level
            
            if confidence:
                update_data['confidence'] = confidence
            
            success = self.db_service.update_document('user_skills', user_skill_id, update_data)
            
            if success:
                # Log activity
                master_skill = self.db_service.get_document('skills_master', skill_id)
                skill_name = master_skill.get('name', skill_id) if master_skill else skill_id
                
                changes = []
                if level:
                    changes.append(f'level to {level}')
                if confidence:
                    changes.append(f'confidence to {confidence}')
                
                self.db_service.log_user_activity(
                    uid, 
                    'SKILL_UPDATED', 
                    f'Updated {skill_name}: {", ".join(changes)}'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating user skill: {str(e)}")
            return False
    
    def remove_user_skill(self, uid: str, skill_id: str) -> bool:
        """Remove a skill from user's profile"""
        try:
            user_skill_id = f"{uid}_{skill_id}"
            
            # Get skill name for logging
            master_skill = self.db_service.get_document('skills_master', skill_id)
            skill_name = master_skill.get('name', skill_id) if master_skill else skill_id
            
            success = self.db_service.delete_document('user_skills', user_skill_id)
            
            if success:
                # Log activity
                self.db_service.log_user_activity(
                    uid, 
                    'SKILL_REMOVED', 
                    f'Removed skill: {skill_name}'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing user skill: {str(e)}")
            return False
    
    def analyze_skill_gaps(self, uid: str, target_role_id: str) -> Dict:
        """Analyze skill gaps for a target role"""
        try:
            # Get user skills
            user_skills = self.get_user_skills(uid)
            user_skill_map = {skill['skillId']: skill for skill in user_skills}
            
            # Get target role requirements (from roadmap_templates or job roles)
            role_template = self.db_service.get_document('roadmap_templates', target_role_id)
            if not role_template:
                logger.warning(f"Role template not found: {target_role_id}")
                return {'error': 'Role not found'}
            
            required_skills = role_template.get('skills', [])
            
            # Analyze gaps
            matched_skills = []
            partial_skills = []
            missing_skills = []
            
            for req_skill in required_skills:
                skill_id = req_skill['skillId']
                required_level = req_skill.get('minLevel', 'beginner')
                
                if skill_id in user_skill_map:
                    user_skill = user_skill_map[skill_id]
                    user_level = user_skill['userLevel']
                    
                    # Compare levels (beginner < intermediate < advanced)
                    level_order = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
                    user_level_score = level_order.get(user_level, 1)
                    required_level_score = level_order.get(required_level, 1)
                    
                    if user_level_score >= required_level_score:
                        matched_skills.append({
                            'skill': user_skill,
                            'required': required_level
                        })
                    else:
                        partial_skills.append({
                            'skill': user_skill,
                            'required': required_level,
                            'gap': required_level_score - user_level_score
                        })
                else:
                    # Get skill details from master catalog
                    master_skill = self.db_service.get_document('skills_master', skill_id)
                    if master_skill:
                        missing_skills.append({
                            'skillId': skill_id,
                            'skillName': master_skill['name'],
                            'required': required_level
                        })
            
            # Calculate readiness score
            total_skills = len(required_skills)
            matched_count = len(matched_skills)
            partial_count = len(partial_skills)
            
            # Weighted scoring: matched = 1.0, partial = 0.5, missing = 0.0
            readiness_score = 0
            if total_skills > 0:
                readiness_score = ((matched_count * 1.0) + (partial_count * 0.5)) / total_skills * 100
            
            return {
                'readinessScore': round(readiness_score, 1),
                'matchedSkills': matched_skills,
                'partialSkills': partial_skills,
                'missingSkills': missing_skills,
                'totalRequired': total_skills,
                'analysis': {
                    'matched': matched_count,
                    'partial': partial_count,
                    'missing': len(missing_skills)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing skill gaps: {str(e)}")
            return {'error': 'Analysis failed'}
    
    def get_skill_categories(self) -> List[str]:
        """Get all available skill categories"""
        try:
            skills = self.get_master_skills()
            categories = set()
            
            for skill in skills:
                category = skill.get('category')
                if category:
                    categories.add(category)
            
            return sorted(list(categories))
            
        except Exception as e:
            logger.error(f"Error getting skill categories: {str(e)}")
            return []
    
    def get_related_skills(self, skill_id: str) -> List[Dict]:
        """Get skills related to a given skill"""
        try:
            master_skill = self.db_service.get_document('skills_master', skill_id)
            if not master_skill:
                return []
            
            related_skill_ids = master_skill.get('relatedSkills', [])
            related_skills = []
            
            for related_id in related_skill_ids:
                related_skill = self.db_service.get_document('skills_master', related_id)
                if related_skill:
                    related_skills.append(related_skill)
            
            return related_skills
            
        except Exception as e:
            logger.error(f"Error getting related skills: {str(e)}")
            return []