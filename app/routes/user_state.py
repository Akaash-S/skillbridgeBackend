from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.user_state_manager import UserStateManager
from app.utils.validators import validate_required_fields
import logging

logger = logging.getLogger(__name__)
user_state_bp = Blueprint('user_state', __name__)
state_manager = UserStateManager()

@user_state_bp.route('', methods=['GET'])
@auth_required
def get_user_state():
    """
    Get comprehensive user state data
    Returns all user data needed for the application
    """
    try:
        uid = request.current_user['uid']
        
        # Get comprehensive user state
        user_state = state_manager.get_user_state(uid)
        
        if not user_state:
            # Initialize state for new users
            state_manager.initialize_user_state(uid)
            user_state = state_manager.get_user_state(uid)
        
        return jsonify({
            'userState': user_state,
            'hasData': user_state is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Get user state error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user state',
            'code': 'GET_USER_STATE_ERROR'
        }), 500

@user_state_bp.route('/dashboard', methods=['GET'])
@auth_required
def get_dashboard_data():
    """
    Get all data needed for user dashboard
    """
    try:
        uid = request.current_user['uid']
        
        dashboard_data = state_manager.get_user_dashboard_data(uid)
        
        return jsonify({
            'dashboardData': dashboard_data
        }), 200
        
    except Exception as e:
        logger.error(f"Get dashboard data error: {str(e)}")
        return jsonify({
            'error': 'Failed to get dashboard data',
            'code': 'GET_DASHBOARD_ERROR'
        }), 500

@user_state_bp.route('/skills', methods=['PUT'])
@auth_required
def update_user_skills_state():
    """
    Update user skills in state
    Expected payload: {
        "skills": [{"skillId": "js", "name": "JavaScript", "proficiency": "intermediate"}]
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['skills']):
            return jsonify({
                'error': 'Missing required field: skills',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        skills = data['skills']
        
        # Update skills in state
        success = state_manager.update_user_skills(uid, skills)
        
        if not success:
            return jsonify({
                'error': 'Failed to update user skills state',
                'code': 'UPDATE_SKILLS_STATE_FAILED'
            }), 500
        
        return jsonify({
            'message': 'User skills state updated successfully',
            'skillsCount': len(skills)
        }), 200
        
    except Exception as e:
        logger.error(f"Update user skills state error: {str(e)}")
        return jsonify({
            'error': 'Failed to update user skills state',
            'code': 'UPDATE_SKILLS_STATE_ERROR'
        }), 500

@user_state_bp.route('/target-role', methods=['PUT'])
@auth_required
def update_target_role_state():
    """
    Update user's target role in state
    Expected payload: {
        "targetRole": {"id": "frontend-dev", "title": "Frontend Developer", ...}
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['targetRole']):
            return jsonify({
                'error': 'Missing required field: targetRole',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        target_role = data['targetRole']
        
        # Update target role in state
        success = state_manager.update_target_role(uid, target_role)
        
        if not success:
            return jsonify({
                'error': 'Failed to update target role state',
                'code': 'UPDATE_TARGET_ROLE_STATE_FAILED'
            }), 500
        
        return jsonify({
            'message': 'Target role state updated successfully',
            'targetRole': target_role
        }), 200
        
    except Exception as e:
        logger.error(f"Update target role state error: {str(e)}")
        return jsonify({
            'error': 'Failed to update target role state',
            'code': 'UPDATE_TARGET_ROLE_STATE_ERROR'
        }), 500

@user_state_bp.route('/analysis', methods=['PUT'])
@auth_required
def update_analysis_state():
    """
    Update user's analysis data in state
    Expected payload: {
        "analysis": {"readinessScore": 75, "matchedSkills": [...], ...}
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['analysis']):
            return jsonify({
                'error': 'Missing required field: analysis',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        analysis_data = data['analysis']
        
        # Update analysis in state
        success = state_manager.update_analysis_data(uid, analysis_data)
        
        if not success:
            return jsonify({
                'error': 'Failed to update analysis state',
                'code': 'UPDATE_ANALYSIS_STATE_FAILED'
            }), 500
        
        return jsonify({
            'message': 'Analysis state updated successfully',
            'readinessScore': analysis_data.get('readinessScore', 0)
        }), 200
        
    except Exception as e:
        logger.error(f"Update analysis state error: {str(e)}")
        return jsonify({
            'error': 'Failed to update analysis state',
            'code': 'UPDATE_ANALYSIS_STATE_ERROR'
        }), 500

@user_state_bp.route('/roadmap-progress', methods=['PUT'])
@auth_required
def update_roadmap_progress_state():
    """
    Update user's roadmap progress in state
    Expected payload: {
        "roadmapProgress": {"totalItems": 10, "completedItems": 3, "progress": 30, ...}
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['roadmapProgress']):
            return jsonify({
                'error': 'Missing required field: roadmapProgress',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        roadmap_progress = data['roadmapProgress']
        
        # Update roadmap progress in state
        success = state_manager.update_roadmap_progress(uid, roadmap_progress)
        
        if not success:
            return jsonify({
                'error': 'Failed to update roadmap progress state',
                'code': 'UPDATE_ROADMAP_PROGRESS_STATE_FAILED'
            }), 500
        
        return jsonify({
            'message': 'Roadmap progress state updated successfully',
            'progress': roadmap_progress.get('progress', 0)
        }), 200
        
    except Exception as e:
        logger.error(f"Update roadmap progress state error: {str(e)}")
        return jsonify({
            'error': 'Failed to update roadmap progress state',
            'code': 'UPDATE_ROADMAP_PROGRESS_STATE_ERROR'
        }), 500

@user_state_bp.route('', methods=['POST'])
@auth_required
def save_complete_user_state():
    """
    Save complete user state
    Expected payload: {
        "skills": [...],
        "targetRole": {...},
        "analysis": {...},
        "roadmapProgress": {...}
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Save complete state
        success = state_manager.save_user_state(uid, data)
        
        if not success:
            return jsonify({
                'error': 'Failed to save user state',
                'code': 'SAVE_USER_STATE_FAILED'
            }), 500
        
        return jsonify({
            'message': 'User state saved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Save user state error: {str(e)}")
        return jsonify({
            'error': 'Failed to save user state',
            'code': 'SAVE_USER_STATE_ERROR'
        }), 500