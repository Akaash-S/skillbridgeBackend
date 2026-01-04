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
        "careerGoal": "string",
        "experienceLevel": "beginner|intermediate|advanced",
        "onboardingCompleted": boolean
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
        
        # Validate experience level if provided
        valid_experience_levels = ['beginner', 'intermediate', 'advanced']
        if 'experienceLevel' in data and data['experienceLevel'] not in valid_experience_levels:
            return jsonify({
                'error': f'Invalid experience level. Must be one of: {", ".join(valid_experience_levels)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Prepare update data
        update_data = {}
        allowed_fields = ['name', 'careerGoal', 'experienceLevel', 'onboardingCompleted']
        
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
        
        # Log activity
        updated_fields = list(update_data.keys())
        db_service.log_user_activity(
            uid, 
            'PROFILE_UPDATED', 
            f'Updated profile fields: {", ".join(updated_fields)}'
        )
        
        # Get updated profile
        updated_profile = db_service.get_document('users', uid)
        
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
        "careerGoal": "string",
        "experienceLevel": "beginner|intermediate|advanced"
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'careerGoal', 'experienceLevel']
        if not validate_required_fields(data, required_fields):
            return jsonify({
                'error': f'Missing required fields: {", ".join(required_fields)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate experience level
        valid_experience_levels = ['beginner', 'intermediate', 'advanced']
        if data['experienceLevel'] not in valid_experience_levels:
            return jsonify({
                'error': f'Invalid experience level. Must be one of: {", ".join(valid_experience_levels)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Update user profile with onboarding data
        update_data = {
            'name': data['name'],
            'careerGoal': data['careerGoal'],
            'experienceLevel': data['experienceLevel'],
            'onboardingCompleted': True,
            'updatedAt': datetime.utcnow()
        }
        
        success = db_service.update_document('users', uid, update_data)
        if not success:
            return jsonify({
                'error': 'Failed to complete onboarding',
                'code': 'ONBOARDING_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'ONBOARDING_COMPLETED', 'User completed onboarding')
        
        # Get updated profile
        updated_profile = db_service.get_document('users', uid)
        
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