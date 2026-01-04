from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.db.firestore import FirestoreService
from app.utils.validators import validate_required_fields
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__)
db_service = FirestoreService()

@settings_bp.route('', methods=['GET'])
@auth_required
def get_settings():
    """Get user settings"""
    try:
        uid = request.current_user['uid']
        
        # Get user settings
        settings = db_service.get_document('settings', uid)
        
        # Return default settings if none exist
        if not settings:
            default_settings = {
                'uid': uid,
                'theme': 'system',
                'learningPace': 'balanced',
                'notifications': True,
                'jobCountries': ['in'],
                'emailNotifications': {
                    'roadmapUpdates': True,
                    'jobRecommendations': True,
                    'learningReminders': True,
                    'weeklyProgress': True
                },
                'privacy': {
                    'profileVisibility': 'private',
                    'skillsVisibility': 'private',
                    'progressVisibility': 'private'
                },
                'preferences': {
                    'language': 'en',
                    'timezone': 'UTC',
                    'weeklyGoal': 10,
                    'difficultyPreference': 'adaptive'
                },
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }
            
            # Create default settings
            db_service.create_document('settings', uid, default_settings)
            return jsonify({'settings': default_settings}), 200
        
        return jsonify({'settings': settings}), 200
        
    except Exception as e:
        logger.error(f"Get settings error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user settings',
            'code': 'GET_SETTINGS_ERROR'
        }), 500

@settings_bp.route('', methods=['PUT'])
@auth_required
def update_settings():
    """
    Update user settings
    Expected payload: {
        "theme": "light|dark|system",
        "learningPace": "slow|balanced|fast",
        "notifications": boolean,
        "jobCountries": ["country_code"],
        "emailNotifications": {
            "roadmapUpdates": boolean,
            "jobRecommendations": boolean,
            "learningReminders": boolean,
            "weeklyProgress": boolean
        },
        "privacy": {
            "profileVisibility": "public|private",
            "skillsVisibility": "public|private",
            "progressVisibility": "public|private"
        },
        "preferences": {
            "language": "string",
            "timezone": "string",
            "weeklyGoal": number,
            "difficultyPreference": "easy|adaptive|challenging"
        }
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
        
        # Validate specific fields if provided
        validation_errors = []
        
        # Validate theme
        if 'theme' in data:
            valid_themes = ['light', 'dark', 'system']
            if data['theme'] not in valid_themes:
                validation_errors.append(f'Invalid theme. Must be one of: {", ".join(valid_themes)}')
        
        # Validate learning pace
        if 'learningPace' in data:
            valid_paces = ['slow', 'balanced', 'fast']
            if data['learningPace'] not in valid_paces:
                validation_errors.append(f'Invalid learning pace. Must be one of: {", ".join(valid_paces)}')
        
        # Validate job countries
        if 'jobCountries' in data:
            if not isinstance(data['jobCountries'], list):
                validation_errors.append('jobCountries must be an array')
            elif len(data['jobCountries']) == 0:
                validation_errors.append('jobCountries cannot be empty')
        
        # Validate privacy settings
        if 'privacy' in data:
            privacy = data['privacy']
            valid_visibility = ['public', 'private']
            
            for field in ['profileVisibility', 'skillsVisibility', 'progressVisibility']:
                if field in privacy and privacy[field] not in valid_visibility:
                    validation_errors.append(f'Invalid {field}. Must be one of: {", ".join(valid_visibility)}')
        
        # Validate preferences
        if 'preferences' in data:
            preferences = data['preferences']
            
            if 'weeklyGoal' in preferences:
                weekly_goal = preferences['weeklyGoal']
                if not isinstance(weekly_goal, int) or weekly_goal < 1 or weekly_goal > 50:
                    validation_errors.append('weeklyGoal must be an integer between 1 and 50')
            
            if 'difficultyPreference' in preferences:
                valid_difficulty = ['easy', 'adaptive', 'challenging']
                if preferences['difficultyPreference'] not in valid_difficulty:
                    validation_errors.append(f'Invalid difficultyPreference. Must be one of: {", ".join(valid_difficulty)}')
        
        if validation_errors:
            return jsonify({
                'error': 'Validation errors',
                'details': validation_errors,
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Get existing settings
        existing_settings = db_service.get_document('settings', uid)
        
        # Prepare update data
        update_data = {}
        allowed_top_level_fields = ['theme', 'learningPace', 'notifications', 'jobCountries']
        
        for field in allowed_top_level_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Handle nested objects
        if 'emailNotifications' in data:
            if existing_settings and 'emailNotifications' in existing_settings:
                update_data['emailNotifications'] = {**existing_settings['emailNotifications'], **data['emailNotifications']}
            else:
                update_data['emailNotifications'] = data['emailNotifications']
        
        if 'privacy' in data:
            if existing_settings and 'privacy' in existing_settings:
                update_data['privacy'] = {**existing_settings['privacy'], **data['privacy']}
            else:
                update_data['privacy'] = data['privacy']
        
        if 'preferences' in data:
            if existing_settings and 'preferences' in existing_settings:
                update_data['preferences'] = {**existing_settings['preferences'], **data['preferences']}
            else:
                update_data['preferences'] = data['preferences']
        
        if not update_data:
            return jsonify({
                'error': 'No valid fields to update',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Add timestamp
        update_data['updatedAt'] = datetime.utcnow()
        
        # Update settings
        if existing_settings:
            success = db_service.update_document('settings', uid, update_data)
        else:
            # Create new settings document
            update_data['uid'] = uid
            update_data['createdAt'] = datetime.utcnow()
            success = db_service.create_document('settings', uid, update_data)
        
        if not success:
            return jsonify({
                'error': 'Failed to update settings',
                'code': 'UPDATE_FAILED'
            }), 500
        
        # Log activity
        updated_fields = list(update_data.keys())
        db_service.log_user_activity(
            uid,
            'SETTINGS_UPDATED',
            f'Updated settings: {", ".join(updated_fields)}'
        )
        
        # Get updated settings
        updated_settings = db_service.get_document('settings', uid)
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': updated_settings
        }), 200
        
    except Exception as e:
        logger.error(f"Update settings error: {str(e)}")
        return jsonify({
            'error': 'Failed to update settings',
            'code': 'UPDATE_SETTINGS_ERROR'
        }), 500

@settings_bp.route('/reset', methods=['POST'])
@auth_required
def reset_settings():
    """Reset user settings to defaults"""
    try:
        uid = request.current_user['uid']
        
        # Default settings
        default_settings = {
            'uid': uid,
            'theme': 'system',
            'learningPace': 'balanced',
            'notifications': True,
            'jobCountries': ['in'],
            'emailNotifications': {
                'roadmapUpdates': True,
                'jobRecommendations': True,
                'learningReminders': True,
                'weeklyProgress': True
            },
            'privacy': {
                'profileVisibility': 'private',
                'skillsVisibility': 'private',
                'progressVisibility': 'private'
            },
            'preferences': {
                'language': 'en',
                'timezone': 'UTC',
                'weeklyGoal': 10,
                'difficultyPreference': 'adaptive'
            },
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        # Update settings with defaults
        success = db_service.create_document('settings', uid, default_settings)
        
        if not success:
            return jsonify({
                'error': 'Failed to reset settings',
                'code': 'RESET_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'SETTINGS_UPDATED', 'Settings reset to defaults')
        
        return jsonify({
            'message': 'Settings reset to defaults successfully',
            'settings': default_settings
        }), 200
        
    except Exception as e:
        logger.error(f"Reset settings error: {str(e)}")
        return jsonify({
            'error': 'Failed to reset settings',
            'code': 'RESET_SETTINGS_ERROR'
        }), 500

@settings_bp.route('/export', methods=['GET'])
@auth_required
def export_settings():
    """Export user settings as JSON"""
    try:
        uid = request.current_user['uid']
        
        settings = db_service.get_document('settings', uid)
        
        if not settings:
            return jsonify({
                'error': 'No settings found to export',
                'code': 'SETTINGS_NOT_FOUND'
            }), 404
        
        # Remove sensitive fields
        export_settings = {k: v for k, v in settings.items() if k not in ['uid', 'createdAt', 'updatedAt']}
        
        return jsonify({
            'settings': export_settings,
            'exportedAt': datetime.utcnow().isoformat(),
            'version': '1.0'
        }), 200
        
    except Exception as e:
        logger.error(f"Export settings error: {str(e)}")
        return jsonify({
            'error': 'Failed to export settings',
            'code': 'EXPORT_SETTINGS_ERROR'
        }), 500