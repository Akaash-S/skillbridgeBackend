import google.generativeai as genai
from app.db.firestore import FirestoreService
from app.config import Config
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RoadmapAI:
    """AI-powered roadmap generation using Gemini"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        
        # Configure Gemini
        api_key = Config.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def generate_roadmap(self, uid: str, target_role: str, user_skills: List[Dict], experience_level: str = 'beginner') -> Dict:
        """Generate AI-powered learning roadmap"""
        try:
            # Get master skills for validation
            master_skills = self.db_service.query_collection('skills_master')
            valid_skill_ids = {skill['skillId'] for skill in master_skills}
            skill_name_map = {skill['skillId']: skill['name'] for skill in master_skills}
            
            # Prepare user skills context
            user_skills_context = []
            for skill in user_skills:
                user_skills_context.append({
                    'name': skill.get('name', skill.get('skillId')),
                    'level': skill.get('userLevel', skill.get('level')),
                    'category': skill.get('category', 'Unknown')
                })
            
            # Create AI prompt
            prompt = self._create_roadmap_prompt(
                target_role, 
                user_skills_context, 
                experience_level,
                list(valid_skill_ids)
            )
            
            # Generate roadmap with Gemini
            response = self.model.generate_content(prompt)
            
            if not response.text:
                logger.error("Empty response from Gemini API")
                return self._get_fallback_roadmap(target_role)
            
            # Parse JSON response
            try:
                ai_roadmap = json.loads(response.text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini JSON response: {str(e)}")
                logger.error(f"Raw response: {response.text}")
                return self._get_fallback_roadmap(target_role)
            
            # Validate and clean roadmap
            validated_roadmap = self._validate_roadmap(ai_roadmap, valid_skill_ids, skill_name_map)
            
            # Save roadmap to Firestore
            roadmap_data = {
                'uid': uid,
                'roleId': target_role,
                'roadmapVersion': 'ai-generated',
                'generatedAt': datetime.utcnow(),
                'milestones': validated_roadmap.get('milestones', []),
                'isActive': True,
                'metadata': {
                    'experienceLevel': experience_level,
                    'totalSkills': len(user_skills),
                    'aiModel': 'gemini-2.0-flash'
                }
            }
            
            # Deactivate existing roadmaps
            self._deactivate_existing_roadmaps(uid)
            
            # Create new roadmap
            roadmap_id = f"{uid}_{target_role}_{int(datetime.utcnow().timestamp())}"
            success = self.db_service.create_document('user_roadmaps', roadmap_id, roadmap_data)
            
            if success:
                # Log activity
                self.db_service.log_user_activity(
                    uid, 
                    'ROADMAP_GENERATED', 
                    f'AI roadmap generated for {target_role}'
                )
                
                return {
                    'roadmapId': roadmap_id,
                    'roadmap': roadmap_data,
                    'source': 'ai-generated'
                }
            else:
                logger.error("Failed to save AI roadmap to Firestore")
                return self._get_fallback_roadmap(target_role)
            
        except Exception as e:
            logger.error(f"Error generating AI roadmap: {str(e)}")
            return self._get_fallback_roadmap(target_role)
    
    def _create_roadmap_prompt(self, target_role: str, user_skills: List[Dict], experience_level: str, valid_skills: List[str]) -> str:
        """Create structured prompt for Gemini AI"""
        
        user_skills_str = json.dumps(user_skills, indent=2) if user_skills else "No skills reported"
        valid_skills_sample = valid_skills[:50]  # Limit for prompt size
        
        prompt = f"""
You are a career development AI creating a personalized learning roadmap for a {target_role} role.

USER PROFILE:
- Target Role: {target_role}
- Experience Level: {experience_level}
- Current Skills: {user_skills_str}

VALID SKILL IDs (use ONLY these):
{json.dumps(valid_skills_sample)}

REQUIREMENTS:
1. Create 4-6 learning milestones
2. Each milestone should have 2-4 skills
3. Order skills by learning dependency
4. Use ONLY skill IDs from the valid list above
5. Include beginner to advanced progression
6. Focus on industry-standard skills for {target_role}

OUTPUT FORMAT (JSON only, no markdown):
{{
  "milestones": [
    {{
      "title": "Foundation Skills",
      "description": "Core programming fundamentals",
      "order": 1,
      "estimatedWeeks": 4,
      "skills": [
        {{
          "skillId": "javascript",
          "targetLevel": "intermediate",
          "priority": "high",
          "estimatedHours": 40
        }}
      ]
    }}
  ]
}}

Generate a comprehensive roadmap focusing on practical, industry-relevant skills.
"""
        return prompt
    
    def _validate_roadmap(self, ai_roadmap: Dict, valid_skill_ids: set, skill_name_map: Dict) -> Dict:
        """Validate and clean AI-generated roadmap"""
        try:
            validated_milestones = []
            
            milestones = ai_roadmap.get('milestones', [])
            
            for milestone in milestones:
                if not isinstance(milestone, dict):
                    continue
                
                validated_skills = []
                skills = milestone.get('skills', [])
                
                for skill in skills:
                    if not isinstance(skill, dict):
                        continue
                    
                    skill_id = skill.get('skillId')
                    
                    # Validate skill exists in master catalog
                    if skill_id in valid_skill_ids:
                        validated_skill = {
                            'skillId': skill_id,
                            'skillName': skill_name_map.get(skill_id, skill_id),
                            'targetLevel': skill.get('targetLevel', 'intermediate'),
                            'priority': skill.get('priority', 'medium'),
                            'estimatedHours': skill.get('estimatedHours', 20),
                            'status': 'not_started',
                            'completed': False
                        }
                        validated_skills.append(validated_skill)
                    else:
                        logger.warning(f"Invalid skill ID removed from roadmap: {skill_id}")
                
                if validated_skills:  # Only include milestones with valid skills
                    validated_milestone = {
                        'title': milestone.get('title', 'Learning Milestone'),
                        'description': milestone.get('description', ''),
                        'order': milestone.get('order', len(validated_milestones) + 1),
                        'estimatedWeeks': milestone.get('estimatedWeeks', 2),
                        'skills': validated_skills,
                        'completed': False
                    }
                    validated_milestones.append(validated_milestone)
            
            return {'milestones': validated_milestones}
            
        except Exception as e:
            logger.error(f"Error validating roadmap: {str(e)}")
            return {'milestones': []}
    
    def _get_fallback_roadmap(self, target_role: str) -> Dict:
        """Get fallback roadmap from templates"""
        try:
            # Try to get template roadmap
            template = self.db_service.get_document('roadmap_templates', target_role)
            
            if template:
                # Convert template to user roadmap format
                milestones = []
                template_skills = template.get('skills', [])
                
                # Group skills into milestones (4 skills per milestone)
                milestone_size = 4
                for i in range(0, len(template_skills), milestone_size):
                    milestone_skills = template_skills[i:i + milestone_size]
                    
                    milestone = {
                        'title': f'Milestone {(i // milestone_size) + 1}',
                        'description': f'Learning phase {(i // milestone_size) + 1}',
                        'order': (i // milestone_size) + 1,
                        'estimatedWeeks': 3,
                        'skills': [
                            {
                                'skillId': skill['skillId'],
                                'skillName': skill.get('skillName', skill['skillId']),
                                'targetLevel': 'intermediate',
                                'priority': 'medium',
                                'estimatedHours': 25,
                                'status': 'not_started',
                                'completed': False
                            }
                            for skill in milestone_skills
                        ],
                        'completed': False
                    }
                    milestones.append(milestone)
                
                return {
                    'roadmap': {
                        'milestones': milestones,
                        'source': 'template-fallback'
                    },
                    'source': 'template'
                }
            
            # Ultimate fallback - basic roadmap
            return {
                'roadmap': {
                    'milestones': [
                        {
                            'title': 'Getting Started',
                            'description': 'Begin your learning journey',
                            'order': 1,
                            'estimatedWeeks': 2,
                            'skills': [],
                            'completed': False
                        }
                    ],
                    'source': 'basic-fallback'
                },
                'source': 'fallback'
            }
            
        except Exception as e:
            logger.error(f"Error getting fallback roadmap: {str(e)}")
            return {
                'roadmap': {'milestones': []},
                'source': 'error'
            }
    
    def _deactivate_existing_roadmaps(self, uid: str):
        """Deactivate existing active roadmaps for user"""
        try:
            existing_roadmaps = self.db_service.query_collection(
                'user_roadmaps', 
                [('uid', '==', uid), ('isActive', '==', True)]
            )
            
            for roadmap in existing_roadmaps:
                # This is a simplified approach - in production, you'd need the document ID
                # For now, we'll assume the roadmap has an ID field
                roadmap_id = roadmap.get('id')
                if roadmap_id:
                    self.db_service.update_document('user_roadmaps', roadmap_id, {'isActive': False})
                    
        except Exception as e:
            logger.error(f"Error deactivating existing roadmaps: {str(e)}")
    
    def update_roadmap_progress(self, uid: str, milestone_index: int, skill_id: str, completed: bool) -> bool:
        """Update progress on a roadmap item"""
        try:
            # Get active roadmap
            roadmaps = self.db_service.query_collection(
                'user_roadmaps',
                [('uid', '==', uid), ('isActive', '==', True)],
                limit=1
            )
            
            if not roadmaps:
                logger.warning(f"No active roadmap found for user: {uid}")
                return False
            
            roadmap = roadmaps[0]
            milestones = roadmap.get('milestones', [])
            
            if milestone_index >= len(milestones):
                logger.warning(f"Invalid milestone index: {milestone_index}")
                return False
            
            # Update skill completion status
            milestone = milestones[milestone_index]
            skills = milestone.get('skills', [])
            
            skill_updated = False
            for skill in skills:
                if skill.get('skillId') == skill_id:
                    skill['completed'] = completed
                    skill['status'] = 'completed' if completed else 'in_progress'
                    skill_updated = True
                    break
            
            if not skill_updated:
                logger.warning(f"Skill not found in milestone: {skill_id}")
                return False
            
            # Check if milestone is completed
            milestone_completed = all(skill.get('completed', False) for skill in skills)
            milestone['completed'] = milestone_completed
            
            # Update roadmap in Firestore
            # Note: This is simplified - you'd need the actual document ID
            roadmap_id = roadmap.get('id')  # Assuming ID is stored in document
            if roadmap_id:
                success = self.db_service.update_document('user_roadmaps', roadmap_id, {
                    'milestones': milestones
                })
                
                if success:
                    # Log activity
                    action = 'completed' if completed else 'started'
                    skill_name = next((s.get('skillName', skill_id) for s in skills if s.get('skillId') == skill_id), skill_id)
                    
                    self.db_service.log_user_activity(
                        uid,
                        'ROADMAP_PROGRESS',
                        f'{action.title()} skill: {skill_name}'
                    )
                
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating roadmap progress: {str(e)}")
            return False