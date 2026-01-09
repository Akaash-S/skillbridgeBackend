from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.roadmap_ai import RoadmapAI
from app.services.skills_engine import SkillsEngine
from app.services.user_state_manager import UserStateManager
from app.db.firestore import FirestoreService
from app.utils.validators import validate_required_fields
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
roadmap_bp = Blueprint('roadmap', __name__)
roadmap_ai = RoadmapAI()
skills_engine = SkillsEngine()
state_manager = UserStateManager()
db_service = FirestoreService()

@roadmap_bp.route('/generate', methods=['POST'])
@auth_required
def generate_roadmap():
    """
    Generate roadmap using pre-built templates (fast)
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
        
        # Use fast template-based generation instead of AI
        from app.services.roadmap_templates import FastRoadmapGenerator
        template_generator = FastRoadmapGenerator()
        
        # Try to get roadmap template from Firestore first, fallback to hardcoded
        roadmap_template = template_generator.load_template_from_firestore(target_role)
        if not roadmap_template:
            # Fallback to hardcoded template
            roadmap_template = template_generator.get_roadmap_template(target_role)
        
        if not roadmap_template:
            return jsonify({
                'error': f'No roadmap template found for role: {target_role}',
                'code': 'TEMPLATE_NOT_FOUND'
            }), 404
        
        # Get user's current skills to customize the roadmap
        user_skills = skills_engine.get_user_skills(uid)
        
        # Customize template based on user's current skills and experience level
        customized_roadmap = template_generator.customize_roadmap(
            roadmap_template, 
            user_skills, 
            experience_level
        )
        
        # Save the roadmap to database
        roadmap_data = {
            'uid': uid,
            'roleId': target_role,
            'experienceLevel': experience_level,
            'milestones': customized_roadmap['milestones'],
            'generatedAt': datetime.utcnow(),
            'roadmapVersion': 'template-based',
            'isActive': True,
            'totalSkills': sum(len(m.get('skills', [])) for m in customized_roadmap['milestones']),
            'estimatedWeeks': sum(m.get('estimatedWeeks', 0) for m in customized_roadmap['milestones'])
        }
        
        # Deactivate any existing roadmaps for this user
        existing_roadmaps = db_service.query_collection(
            'user_roadmaps',
            [('uid', '==', uid), ('isActive', '==', True)]
        )
        
        for existing in existing_roadmaps:
            if existing.get('id'):
                db_service.update_document('user_roadmaps', existing['id'], {'isActive': False})
        
        # Save new roadmap
        roadmap_id = f"{uid}_{target_role}_{int(datetime.utcnow().timestamp())}"
        success = db_service.create_document('user_roadmaps', roadmap_id, roadmap_data)
        
        # Convert to frontend RoadmapItem format
        roadmap_items = []
        for milestone in customized_roadmap['milestones']:
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
        
        # Log activity
        db_service.log_user_activity(uid, 'ROADMAP_GENERATED', f'Generated roadmap for {target_role}')
        
        # Save roadmap to user state
        roadmap_state_data = {
            'targetRole': target_role,
            'experienceLevel': experience_level,
            'totalItems': len(roadmap_items),
            'completedItems': 0,
            'progress': 0,
            'roadmapItems': roadmap_items,
            'generatedAt': datetime.utcnow(),
            'lastUpdated': datetime.utcnow()
        }
        state_manager.update_roadmap_progress(uid, roadmap_state_data)
        
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
    Update roadmap progress and trigger analysis update
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
        
        # Update progress (the roadmap_ai service will find the correct milestone)
        success = roadmap_ai.update_roadmap_progress(uid, milestone_index, skill_id, completed)
        
        if not success:
            return jsonify({
                'error': 'Failed to update roadmap progress. Skill may not exist in roadmap.',
                'code': 'UPDATE_PROGRESS_FAILED',
                'skillId': skill_id
            }), 400
        
        # If skill was completed, update analysis
        if completed:
            from app.services.analysis_tracker import AnalysisTracker
            analysis_tracker = AnalysisTracker()
            
            # Get user's active roadmap to find the target role
            active_roadmap = db_service.get_user_roadmap(uid)
            if active_roadmap:
                role_id = active_roadmap.get('roleId')
                if role_id:
                    # Update analysis based on completion
                    analysis_updated = analysis_tracker.update_analysis_on_completion(uid, role_id, skill_id)
                    if analysis_updated:
                        logger.info(f"Updated analysis for user {uid} after completing skill {skill_id}")
        
        # Update roadmap progress in user state
        user_state = state_manager.get_user_state(uid)
        if user_state and user_state.get('roadmapProgress'):
            roadmap_progress = user_state['roadmapProgress']
            roadmap_items = roadmap_progress.get('roadmapItems', [])
            
            # Update the specific item
            for item in roadmap_items:
                if item.get('skillId') == skill_id:
                    item['completed'] = completed
                    break
            
            # Recalculate progress
            total_items = len(roadmap_items)
            completed_items = sum(1 for item in roadmap_items if item.get('completed', False))
            progress = (completed_items / total_items * 100) if total_items > 0 else 0
            
            # Update roadmap progress
            roadmap_progress.update({
                'completedItems': completed_items,
                'progress': round(progress, 1),
                'roadmapItems': roadmap_items,
                'lastUpdated': datetime.utcnow()
            })
            
            state_manager.update_roadmap_progress(uid, roadmap_progress)
        
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
        from app.services.roadmap_templates import FastRoadmapGenerator
        template_generator = FastRoadmapGenerator()
        
        # Get all templates
        templates = template_generator.get_all_templates()
        
        # Format templates for response
        formatted_templates = []
        for role_id, template in templates.items():
            milestone_count = len(template['milestones'])
            total_skills = sum(len(m.get('skills', [])) for m in template['milestones'])
            total_weeks = sum(m.get('estimatedWeeks', 0) for m in template['milestones'])
            
            formatted_template = {
                'roleId': role_id,
                'title': template['title'],
                'description': template.get('description', ''),
                'milestoneCount': milestone_count,
                'skillCount': total_skills,
                'estimatedWeeks': total_weeks,
                'difficulty': 'intermediate'  # Default difficulty
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

@roadmap_bp.route('/progress/stats', methods=['GET'])
@auth_required
def get_roadmap_progress_stats():
    """Get roadmap progress statistics for analysis page"""
    try:
        uid = request.current_user['uid']
        
        # Get active roadmap
        roadmap = db_service.get_user_roadmap(uid)
        
        if not roadmap:
            return jsonify({
                'hasRoadmap': False,
                'progress': None
            }), 200
        
        # Calculate detailed progress statistics
        milestones = roadmap.get('milestones', [])
        total_skills = 0
        completed_skills = 0
        in_progress_skills = 0
        total_milestones = len(milestones)
        completed_milestones = 0
        
        # Track skills by difficulty level
        difficulty_stats = {
            'beginner': {'total': 0, 'completed': 0},
            'intermediate': {'total': 0, 'completed': 0},
            'advanced': {'total': 0, 'completed': 0}
        }
        
        # Recent activity (last 7 days)
        recent_completions = []
        
        for milestone_idx, milestone in enumerate(milestones):
            skills = milestone.get('skills', [])
            total_skills += len(skills)
            
            milestone_completed = True
            for skill in skills:
                # Count by difficulty
                difficulty = skill.get('targetLevel', 'intermediate')
                if difficulty in difficulty_stats:
                    difficulty_stats[difficulty]['total'] += 1
                
                if skill.get('completed', False):
                    completed_skills += 1
                    if difficulty in difficulty_stats:
                        difficulty_stats[difficulty]['completed'] += 1
                    
                    # Check if completed recently
                    completed_at = skill.get('completedAt')
                    if completed_at:
                        recent_completions.append({
                            'skillId': skill['skillId'],
                            'skillName': skill.get('skillName', skill['skillId']),
                            'completedAt': completed_at,
                            'milestone': milestone.get('title', f'Milestone {milestone_idx + 1}')
                        })
                elif skill.get('inProgress', False):
                    in_progress_skills += 1
                    milestone_completed = False
                else:
                    milestone_completed = False
            
            if milestone_completed and skills:
                completed_milestones += 1
        
        # Calculate progress percentages
        skill_progress = (completed_skills / total_skills * 100) if total_skills > 0 else 0
        milestone_progress = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
        
        # Calculate estimated completion time
        remaining_skills = total_skills - completed_skills
        avg_hours_per_skill = 15  # Average estimate
        estimated_hours_remaining = remaining_skills * avg_hours_per_skill
        
        # Get roadmap metadata
        roadmap_metadata = {
            'targetRole': roadmap.get('roleId', ''),
            'generatedAt': roadmap.get('generatedAt', ''),
            'lastUpdated': roadmap.get('lastUpdated', ''),
            'version': roadmap.get('roadmapVersion', 'ai-generated')
        }
        
        progress_stats = {
            'hasRoadmap': True,
            'progress': {
                'overall': {
                    'skillProgress': round(skill_progress, 1),
                    'milestoneProgress': round(milestone_progress, 1),
                    'totalSkills': total_skills,
                    'completedSkills': completed_skills,
                    'inProgressSkills': in_progress_skills,
                    'remainingSkills': total_skills - completed_skills,
                    'totalMilestones': total_milestones,
                    'completedMilestones': completed_milestones
                },
                'byDifficulty': difficulty_stats,
                'timeEstimate': {
                    'estimatedHoursRemaining': estimated_hours_remaining,
                    'estimatedWeeksRemaining': round(estimated_hours_remaining / 10, 1)  # Assuming 10 hours/week
                },
                'recentActivity': recent_completions[-5:],  # Last 5 completions
                'roadmapMetadata': roadmap_metadata
            }
        }
        
        return jsonify(progress_stats), 200
        
    except Exception as e:
        logger.error(f"Get roadmap progress stats error: {str(e)}")
        return jsonify({
            'error': 'Failed to get roadmap progress statistics',
            'code': 'GET_PROGRESS_STATS_ERROR'
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