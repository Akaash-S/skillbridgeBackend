import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.db.firestore import FirestoreService
from app.services.learning_service import LearningService

logger = logging.getLogger(__name__)

class ModuleService:
    """Service to handle roadmap modules, locking/unlocking, and progress calculations"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        self.learning_service = LearningService()
        
    def get_or_initialize_modules(self, uid: str) -> List[Dict[str, Any]]:
        """Retrieve modules for the user's active roadmap, initializing them if missing"""
        try:
            active_roadmap = self.db_service.get_user_roadmap(uid)
            if not active_roadmap:
                logger.warning(f"No active roadmap found for user {uid}")
                return []
                
            milestones = active_roadmap.get('milestones', [])
            roadmap_modules = active_roadmap.get('roadmapModules', [])
            roadmap_id = active_roadmap.get('id')
            if not roadmap_id:
                # Firestore query result dict will have 'id' injected by query_collection
                roadmap_id = active_roadmap.get('id', f"{uid}_{active_roadmap.get('roleId')}")
                
            # If roadmapModules is not present, initialize it
            if not roadmap_modules and milestones:
                logger.info(f"Initializing roadmap modules for user {uid}")
                roadmap_modules = []
                previous_passed = True
                for i, milestone in enumerate(milestones):
                    m_completed = milestone.get('completed', False)
                    unlocked = previous_passed
                    # For existing completed milestones, automatically pass the quiz
                    quiz_passed = m_completed
                    
                    roadmap_modules.append({
                        'title': milestone.get('title', f"Module {i+1}"),
                        'description': milestone.get('description', ''),
                        'completed': m_completed,
                        'unlocked': unlocked,
                        'quizPassed': quiz_passed
                    })
                    previous_passed = quiz_passed
                    
                # Save initial modules to DB and update state cache
                self._update_roadmap_in_db(uid, roadmap_id, active_roadmap, roadmap_modules)
            
            # Format and enrich modules with skills and learning resources for the frontend
            enriched_modules = []
            for i, module_meta in enumerate(roadmap_modules):
                if i >= len(milestones):
                    break
                milestone = milestones[i]
                
                module_skills = []
                for skill in milestone.get('skills', []):
                    skill_id = skill['skillId']
                    resources = self.learning_service.get_learning_resources(skill_id)
                    
                    formatted_resources = []
                    for res in resources:
                        formatted_resources.append({
                            'id': res.get('id', ''),
                            'title': res.get('title', 'Learning Resource'),
                            'url': res.get('url', ''),
                            'type': res.get('type', 'course'),
                            'duration': res.get('duration', ''),
                            'provider': res.get('provider', '')
                        })
                        
                    module_skills.append({
                        'skillId': skill_id,
                        'skillName': skill.get('skillName', skill_id),
                        'completed': skill.get('completed', False),
                        'resources': formatted_resources
                    })
                    
                enriched_modules.append({
                    'index': i,
                    'title': module_meta.get('title', f"Module {i+1}"),
                    'description': module_meta.get('description', ''),
                    'completed': module_meta.get('completed', False),
                    'unlocked': module_meta.get('unlocked', False),
                    'quizPassed': module_meta.get('quizPassed', False),
                    'skills': module_skills
                })
                
            return enriched_modules
            
        except Exception as e:
            logger.error(f"Error getting or initializing modules for user {uid}: {str(e)}")
            return []
            
    def complete_module(self, uid: str, module_index: int) -> bool:
        """Mark a module's learning resource phase as completed"""
        try:
            active_roadmap = self.db_service.get_user_roadmap(uid)
            if not active_roadmap:
                logger.warning(f"No active roadmap found for user {uid}")
                return False
                
            roadmap_modules = active_roadmap.get('roadmapModules', [])
            if not roadmap_modules or module_index < 0 or module_index >= len(roadmap_modules):
                logger.warning(f"Invalid module index {module_index} for user {uid}")
                return False
                
            roadmap_modules[module_index]['completed'] = True
            
            roadmap_id = active_roadmap.get('id')
            if not roadmap_id:
                roadmap_id = f"{uid}_{active_roadmap.get('roleId')}"
                
            self._update_roadmap_in_db(uid, roadmap_id, active_roadmap, roadmap_modules)
            logger.info(f"Marked module {module_index} completed for user {uid}")
            return True
        except Exception as e:
            logger.error(f"Error completing module {module_index} for user {uid}: {str(e)}")
            return False
            
    def pass_module_quiz(self, uid: str, module_index: int) -> bool:
        """Mark a module's quiz as passed and unlock the next module"""
        try:
            active_roadmap = self.db_service.get_user_roadmap(uid)
            if not active_roadmap:
                return False
                
            roadmap_modules = active_roadmap.get('roadmapModules', [])
            if not roadmap_modules or module_index < 0 or module_index >= len(roadmap_modules):
                return False
                
            roadmap_modules[module_index]['quizPassed'] = True
            roadmap_modules[module_index]['completed'] = True
            
            # Unlock the next module
            if module_index + 1 < len(roadmap_modules):
                roadmap_modules[module_index + 1]['unlocked'] = True
                
            roadmap_id = active_roadmap.get('id')
            if not roadmap_id:
                roadmap_id = f"{uid}_{active_roadmap.get('roleId')}"
                
            self._update_roadmap_in_db(uid, roadmap_id, active_roadmap, roadmap_modules)
            logger.info(f"Passed quiz for module {module_index} and unlocked next module for user {uid}")
            return True
        except Exception as e:
            logger.error(f"Error passing quiz for module {module_index}: {str(e)}")
            return False
            
    def _update_roadmap_in_db(self, uid: str, roadmap_id: str, active_roadmap: Dict, roadmap_modules: List[Dict]):
        """Recalculate progress statistics and save the roadmap update to DB and user state cache"""
        milestones = active_roadmap.get('milestones', [])
        total_skills = 0
        completed_skills = 0
        total_milestones = len(milestones)
        completed_milestones = 0
        
        for idx, milestone in enumerate(milestones):
            skills = milestone.get('skills', [])
            total_skills += len(skills)
            
            # If module is completed, ensure all of its skills are also completed
            m_completed = roadmap_modules[idx].get('completed', False)
            for skill in skills:
                if m_completed:
                    skill['completed'] = True
                    skill['status'] = 'completed'
                if skill.get('completed', False):
                    completed_skills += 1
                    
            milestone['completed'] = m_completed
            if m_completed:
                completed_milestones += 1
                
        skill_progress = (completed_skills / total_skills * 100) if total_skills > 0 else 0
        milestone_progress = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
        
        total_modules = len(roadmap_modules)
        completed_modules = sum(1 for m in roadmap_modules if m.get('completed', False))
        quiz_passed_count = sum(1 for m in roadmap_modules if m.get('quizPassed', False))
        
        progress_obj = {
            'skillProgress': round(skill_progress, 1),
            'milestoneProgress': round(milestone_progress, 1),
            'learningProgress': round(skill_progress, 1),
            'moduleProgress': round((completed_modules / total_modules * 100), 1) if total_modules > 0 else 0,
            'quizProgress': round((quiz_passed_count / total_modules * 100), 1) if total_modules > 0 else 0,
            'totalSkills': total_skills,
            'completedSkills': completed_skills,
            'totalMilestones': total_milestones,
            'completedMilestones': completed_milestones,
            'totalModules': total_modules,
            'completedModules': completed_modules,
            'passedQuizzes': quiz_passed_count
        }
        
        # Save to user_roadmaps
        self.db_service.update_document('user_roadmaps', roadmap_id, {
            'milestones': milestones,
            'roadmapModules': roadmap_modules,
            'progress': progress_obj,
            'lastUpdated': datetime.utcnow()
        })
        
        # Save to state manager cache
        from app.services.user_state_manager import UserStateManager
        state_manager = UserStateManager()
        
        roadmap_items = []
        for milestone in milestones:
            for skill in milestone.get('skills', []):
                roadmap_items.append({
                    'id': f"roadmap-{skill['skillId']}",
                    'skillId': skill['skillId'],
                    'skillName': skill.get('skillName', skill['skillId']),
                    'resources': skill.get('resources', []),
                    'difficulty': skill.get('targetLevel', 'intermediate'),
                    'estimatedTime': f"{skill.get('estimatedHours', 20)} hours",
                    'completed': skill.get('completed', False)
                })
                
        roadmap_state_data = {
            'targetRole': active_roadmap.get('roleId'),
            'experienceLevel': active_roadmap.get('experienceLevel', 'beginner'),
            'totalItems': len(roadmap_items),
            'completedItems': completed_skills,
            'progress': round(skill_progress, 1),
            'learningProgress': round(skill_progress, 1),
            'moduleProgress': round((completed_modules / total_modules * 100), 1) if total_modules > 0 else 0,
            'quizProgress': round((quiz_passed_count / total_modules * 100), 1) if total_modules > 0 else 0,
            'roadmapItems': roadmap_items,
            'roadmapModules': roadmap_modules,
            'lastUpdated': datetime.utcnow()
        }
        state_manager.update_roadmap_progress(uid, roadmap_state_data)
