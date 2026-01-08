from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.db.firestore import FirestoreService
from app.utils.validators import validate_required_fields, validate_email
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__)
db_service = FirestoreService()

@users_bp.route('/profile', methods=['GET'])
@auth_required
def get_profile():
    """Get user profile"""
    try:
        uid = request.current_user['uid']
        
        user_profile = db_service.get_document('users', uid)
        if not user_profile:
            return jsonify({
                'error': 'User profile not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        return jsonify({
            'profile': user_profile
        }), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user profile',
            'code': 'GET_PROFILE_ERROR'
        }), 500

@users_bp.route('/profile', methods=['PUT'])
@auth_required
def update_profile():
    """
    Update user profile
    Expected payload: {
        "name": "string",
        "email": "string",
        "avatar": "string",
        "education": "string",
        "experience": "string",
        "interests": ["string"],
        "notifications": boolean,
        "weeklyGoal": number,
        "careerGoal": "string" (optional, for backward compatibility),
        "experienceLevel": "string" (optional, for backward compatibility),
        "onboardingCompleted": boolean (optional)
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate email if provided
        if 'email' in data and data['email']:
            if not validate_email(data['email']):
                return jsonify({
                    'error': 'Invalid email format',
                    'code': 'VALIDATION_ERROR'
                }), 400
        
        # Validate experience level if provided (backward compatibility)
        valid_experience_levels = ['beginner', 'intermediate', 'advanced']
        if 'experienceLevel' in data and data['experienceLevel'] not in valid_experience_levels:
            return jsonify({
                'error': f'Invalid experience level. Must be one of: {", ".join(valid_experience_levels)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate weekly goal if provided
        if 'weeklyGoal' in data:
            try:
                weekly_goal = int(data['weeklyGoal'])
                if weekly_goal < 1 or weekly_goal > 40:
                    return jsonify({
                        'error': 'Weekly goal must be between 1 and 40 hours',
                        'code': 'VALIDATION_ERROR'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': 'Weekly goal must be a valid number',
                    'code': 'VALIDATION_ERROR'
                }), 400
        
        # Validate interests if provided
        if 'interests' in data and not isinstance(data['interests'], list):
            return jsonify({
                'error': 'Interests must be an array',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Prepare update data
        update_data = {}
        allowed_fields = [
            'name', 'email', 'avatar', 'education', 'experience', 'interests',
            'notifications', 'weeklyGoal', 'careerGoal', 'experienceLevel', 
            'onboardingCompleted'
        ]
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({
                'error': 'No valid fields to update',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Add timestamp
        update_data['updatedAt'] = datetime.utcnow()
        
        # Update profile
        success = db_service.update_document('users', uid, update_data)
        if not success:
            return jsonify({
                'error': 'Failed to update profile',
                'code': 'UPDATE_FAILED'
            }), 500
        
        # Update user state with profile changes
        from app.services.user_state_manager import UserStateManager
        state_manager = UserStateManager()
        
        # Get updated profile
        updated_profile = db_service.get_document('users', uid)
        
        # Update user state if profile data affects it
        if any(field in update_data for field in ['name', 'email', 'avatar', 'education', 'experience', 'interests']):
            user_state = state_manager.get_user_state(uid)
            if user_state:
                # Update profile data in user state
                profile_data = {
                    'name': updated_profile.get('name', ''),
                    'email': updated_profile.get('email', ''),
                    'avatar': updated_profile.get('avatar', ''),
                    'education': updated_profile.get('education', ''),
                    'experience': updated_profile.get('experience', ''),
                    'interests': updated_profile.get('interests', [])
                }
                
                state_update = {
                    'profile': profile_data,
                    'preferences': {
                        'notifications': updated_profile.get('notifications', True),
                        'weeklyGoal': updated_profile.get('weeklyGoal', 10)
                    }
                }
                
                # Update user state
                current_state = state_manager.get_user_state(uid) or {}
                current_state.update(state_update)
                state_manager.save_user_state(uid, current_state)
        
        # Log activity
        updated_fields = [field for field in update_data.keys() if field != 'updatedAt']
        db_service.log_user_activity(
            uid, 
            'PROFILE_UPDATED', 
            f'Updated profile fields: {", ".join(updated_fields)}'
        )
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': updated_profile
        }), 200
        
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return jsonify({
            'error': 'Failed to update profile',
            'code': 'UPDATE_PROFILE_ERROR'
        }), 500

@users_bp.route('/onboarding', methods=['POST'])
@auth_required
def complete_onboarding():
    """
    Complete user onboarding
    Expected payload: {
        "name": "string",
        "education": "string",
        "experience": "string", 
        "interests": ["string"]
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'education', 'experience', 'interests']
        if not validate_required_fields(data, required_fields):
            return jsonify({
                'error': f'Missing required fields: {", ".join(required_fields)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate interests is an array
        if not isinstance(data['interests'], list):
            return jsonify({
                'error': 'Interests must be an array',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate that at least one interest is selected
        if len(data['interests']) == 0:
            return jsonify({
                'error': 'At least one interest must be selected',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Update user profile with onboarding data
        update_data = {
            'name': data['name'],
            'education': data['education'],
            'experience': data['experience'],
            'interests': data['interests'],
            'onboardingCompleted': True,
            'updatedAt': datetime.utcnow()
        }
        
        success = db_service.update_document('users', uid, update_data)
        if not success:
            return jsonify({
                'error': 'Failed to complete onboarding',
                'code': 'ONBOARDING_FAILED'
            }), 500
        
        # Update user state with onboarding data
        from app.services.user_state_manager import UserStateManager
        state_manager = UserStateManager()
        
        # Get updated profile
        updated_profile = db_service.get_document('users', uid)
        
        # Update user state with profile data
        if updated_profile:
            profile_data = {
                'name': updated_profile.get('name', ''),
                'email': updated_profile.get('email', ''),
                'avatar': updated_profile.get('avatar', ''),
                'education': updated_profile.get('education', ''),
                'experience': updated_profile.get('experience', ''),
                'interests': updated_profile.get('interests', [])
            }
            
            preferences_data = {
                'notifications': updated_profile.get('notifications', True),
                'weeklyGoal': updated_profile.get('weeklyGoal', 10)
            }
            
            # Initialize or update user state
            user_state = state_manager.get_user_state(uid) or {}
            user_state.update({
                'profile': profile_data,
                'preferences': preferences_data,
                'onboardingCompleted': True
            })
            
            state_manager.save_user_state(uid, user_state)
        
        # Log activity
        db_service.log_user_activity(uid, 'ONBOARDING_COMPLETED', 'User completed onboarding')
        
        return jsonify({
            'message': 'Onboarding completed successfully',
            'profile': updated_profile
        }), 200
        
    except Exception as e:
        logger.error(f"Complete onboarding error: {str(e)}")
        return jsonify({
            'error': 'Failed to complete onboarding',
            'code': 'ONBOARDING_ERROR'
        }), 500

@users_bp.route('/stats', methods=['GET'])
@auth_required
def get_user_stats():
    """Get user statistics (skills count, roadmap progress, etc.)"""
    try:
        uid = request.current_user['uid']
        
        # Get user skills count
        user_skills = db_service.get_user_skills(uid)
        skills_count = len(user_skills)
        
        # Get skills by proficiency level
        skills_by_level = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
        for skill in user_skills:
            level = skill.get('level', 'beginner')
            if level in skills_by_level:
                skills_by_level[level] += 1
        
        # Get roadmap progress
        roadmap = db_service.get_user_roadmap(uid)
        roadmap_progress = 0
        total_milestones = 0
        completed_milestones = 0
        
        if roadmap and 'milestones' in roadmap:
            total_milestones = len(roadmap['milestones'])
            for milestone in roadmap['milestones']:
                if milestone.get('completed', False):
                    completed_milestones += 1
            
            if total_milestones > 0:
                roadmap_progress = (completed_milestones / total_milestones) * 100
        
        # Get recent activity count
        recent_activity = db_service.get_user_activity(uid, limit=10)
        
        stats = {
            'skillsCount': skills_count,
            'skillsByLevel': skills_by_level,
            'roadmapProgress': round(roadmap_progress, 1),
            'totalMilestones': total_milestones,
            'completedMilestones': completed_milestones,
            'recentActivityCount': len(recent_activity)
        }
        
        return jsonify({
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Get user stats error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user statistics',
            'code': 'GET_STATS_ERROR'
        }), 500