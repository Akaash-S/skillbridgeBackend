from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.roadmap_ai import RoadmapAI
from app.services.skills_engine import SkillsEngine
from app.db.firestore import FirestoreService
from app.utils.validators import validate_required_fields
import logging

logger = logging.getLogger(__name__)
roadmap_bp = Blueprint('roadmap', __name__)
roadmap_ai = RoadmapAI()
skills_engine = SkillsEngine()
db_service = FirestoreService()

@roadmap_bp.route('/generate', methods=['POST'])
@auth_required
def generate_roadmap():
    """
    Generate AI-powered learning roadmap
    Expected payload: {
        "targetRole": "string",
        "experienceLevel": "beginner|intermediate|advanced" (optional)
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Validate required fields
        if not validate_required_fields(data, ['targetRole']):
            return jsonify({
                'error': 'Missing required field: targetRole',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        target_role = data['targetRole']
        experience_level = data.get('experienceLevel', 'beginner')
        
        # Validate experience level
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if experience_level not in valid_levels:
            return jsonify({
                'error': f'Invalid experience level. Must be one of: {", ".join(valid_levels)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Get user's current skills
        user_skills = skills_engine.get_user_skills(uid)
        
        # Generate roadmap using AI
        result = roadmap_ai.generate_roadmap(uid, target_role, user_skills, experience_level)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'code': 'ROADMAP_GENERATION_FAILED'
            }), 500
        
        # Format roadmap for frontend compatibility
        roadmap_data = result.get('roadmap', {})
        milestones = roadmap_data.get('milestones', [])
        
        # Convert to frontend RoadmapItem format
        roadmap_items = []
        for milestone in milestones:
            for skill in milestone.get('skills', []):
                # Get learning resources for this skill
                resources = db_service.query_collection('learning_resources', [('skillId', '==', skill['skillId'])])
                
                # Format resources for frontend
                formatted_resources = []
                for resource in resources:
                    formatted_resource = {
                        'id': resource.get('id', ''),
                        'title': resource.get('title', ''),
                        'url': resource.get('url', ''),
                        'type': resource.get('type', 'course'),
                        'duration': resource.get('duration', ''),
                        'provider': resource.get('provider', '')
                    }
                    formatted_resources.append(formatted_resource)
                
                roadmap_item = {
                    'id': f"roadmap-{skill['skillId']}",
                    'skillId': skill['skillId'],
                    'skillName': skill.get('skillName', skill['skillId']),
                    'resources': formatted_resources,
                    'difficulty': skill.get('targetLevel', 'intermediate'),
                    'estimatedTime': f"{skill.get('estimatedHours', 20)} hours",
                    'completed': False
                }
                roadmap_items.append(roadmap_item)
        
        return jsonify(roadmap_items), 201
        
    except Exception as e:
        logger.error(f"Generate roadmap error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate roadmap',
            'code': 'GENERATE_ROADMAP_ERROR'
        }), 500

@roadmap_bp.route('', methods=['GET'])
@auth_required
def get_roadmap():
    """Get user's active roadmap"""
    try:
        uid = request.current_user['uid']
        
        # Get active roadmap
        roadmap = db_service.get_user_roadmap(uid)
        
        if not roadmap:
            return jsonify({
                'message': 'No active roadmap found',
                'roadmap': None
            }), 200
        
        # Calculate progress statistics
        milestones = roadmap.get('milestones', [])
        total_skills = 0
        completed_skills = 0
        total_milestones = len(milestones)
        completed_milestones = 0
        
        for milestone in milestones:
            skills = milestone.get('skills', [])
            total_skills += len(skills)
            
            milestone_completed = True
            for skill in skills:
                if skill.get('completed', False):
                    completed_skills += 1
                else:
                    milestone_completed = False
            
            if milestone_completed and skills:  # Only count as completed if has skills
                completed_milestones += 1
        
        # Calculate progress percentages
        skill_progress = (completed_skills / total_skills * 100) if total_skills > 0 else 0
        milestone_progress = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
        
        roadmap_with_stats = {
            **roadmap,
            'progress': {
                'skillProgress': round(skill_progress, 1),
                'milestoneProgress': round(milestone_progress, 1),
                'totalSkills': total_skills,
                'completedSkills': completed_skills,
                'totalMilestones': total_milestones,
                'completedMilestones': completed_milestones
            }
        }
        
        return jsonify({
            'roadmap': roadmap_with_stats
        }), 200
        
    except Exception as e:
        logger.error(f"Get roadmap error: {str(e)}")
        return jsonify({
            'error': 'Failed to get roadmap',
            'code': 'GET_ROADMAP_ERROR'
        }), 500

@roadmap_bp.route('/progress', methods=['PUT'])
@auth_required
def update_progress():
    """
    Update roadmap progress
    Expected payload: {
        "milestoneIndex": number,
        "skillId": "string",
        "completed": boolean
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['milestoneIndex', 'skillId', 'completed']
        if not validate_required_fields(data, required_fields):
            return jsonify({
                'error': f'Missing required fields: {", ".join(required_fields)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        milestone_index = data['milestoneIndex']
        skill_id = data['skillId']
        completed = data['completed']
        
        # Validate types
        if not isinstance(milestone_index, int) or milestone_index < 0:
            return jsonify({
                'error': 'milestoneIndex must be a non-negative integer',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        if not isinstance(completed, bool):
            return jsonify({
                'error': 'completed must be a boolean',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Update progress
        success = roadmap_ai.update_roadmap_progress(uid, milestone_index, skill_id, completed)
        
        if not success:
            return jsonify({
                'error': 'Failed to update roadmap progress',
                'code': 'UPDATE_PROGRESS_FAILED'
            }), 400
        
        return jsonify({
            'message': 'Roadmap progress updated successfully',
            'milestoneIndex': milestone_index,
            'skillId': skill_id,
            'completed': completed
        }), 200
        
    except Exception as e:
        logger.error(f"Update roadmap progress error: {str(e)}")
        return jsonify({
            'error': 'Failed to update roadmap progress',
            'code': 'UPDATE_PROGRESS_ERROR'
        }), 500

@roadmap_bp.route('/templates', methods=['GET'])
@auth_required
def get_roadmap_templates():
    """Get available roadmap templates"""
    try:
        # Get all roadmap templates
        templates = db_service.query_collection('roadmap_templates')
        
        # Format templates for response
        formatted_templates = []
        for template in templates:
            formatted_template = {
                'roleId': template.get('roleId'),
                'title': template.get('title'),
                'description': template.get('description', ''),
                'skillCount': len(template.get('skills', [])),
                'estimatedWeeks': template.get('estimatedWeeks', 8),
                'difficulty': template.get('difficulty', 'intermediate')
            }
            formatted_templates.append(formatted_template)
        
        return jsonify({
            'templates': formatted_templates
        }), 200
        
    except Exception as e:
        logger.error(f"Get roadmap templates error: {str(e)}")
        return jsonify({
            'error': 'Failed to get roadmap templates',
            'code': 'GET_TEMPLATES_ERROR'
        }), 500

@roadmap_bp.route('/reset', methods=['POST'])
@auth_required
def reset_roadmap():
    """Reset/deactivate current roadmap"""
    try:
        uid = request.current_user['uid']
        
        # Get active roadmaps
        active_roadmaps = db_service.query_collection(
            'user_roadmaps',
            [('uid', '==', uid), ('isActive', '==', True)]
        )
        
        # Deactivate all active roadmaps
        deactivated_count = 0
        for roadmap in active_roadmaps:
            # Note: This is simplified - you'd need the actual document ID
            roadmap_id = roadmap.get('id')
            if roadmap_id:
                success = db_service.update_document('user_roadmaps', roadmap_id, {
                    'isActive': False,
                    'deactivatedAt': datetime.utcnow()
                })
                if success:
                    deactivated_count += 1
        
        # Log activity
        if deactivated_count > 0:
            db_service.log_user_activity(uid, 'ROADMAP_RESET', 'Roadmap reset by user')
        
        return jsonify({
            'message': f'Roadmap reset successfully. {deactivated_count} roadmap(s) deactivated.',
            'deactivatedCount': deactivated_count
        }), 200
        
    except Exception as e:
        logger.error(f"Reset roadmap error: {str(e)}")
        return jsonify({
            'error': 'Failed to reset roadmap',
            'code': 'RESET_ROADMAP_ERROR'
        }), 500