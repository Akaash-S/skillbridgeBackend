from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.learning_service import LearningService
from app.utils.validators import validate_required_fields
import logging

logger = logging.getLogger(__name__)
learning_bp = Blueprint('learning', __name__)
learning_service = LearningService()

@learning_bp.route('/<skill_id>', methods=['GET'])
@auth_required
def get_learning_resources(skill_id):
    """
    Get learning resources for a specific skill
    Query params:
    - level: beginner|intermediate|advanced (optional)
    - type: course|tutorial|documentation|video (optional)
    """
    try:
        level = request.args.get('level')
        resource_type = request.args.get('type')
        
        resources = learning_service.get_learning_resources(skill_id, level, resource_type)
        
        return jsonify({
            'skillId': skill_id,
            'resources': resources,
            'filters': {
                'level': level,
                'type': resource_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get learning resources error: {str(e)}")
        return jsonify({
            'error': 'Failed to get learning resources',
            'code': 'GET_RESOURCES_ERROR'
        }), 500

@learning_bp.route('/search', methods=['GET'])
@auth_required
def search_learning_resources():
    """
    Search learning resources
    Query params:
    - q: search query (required)
    - limit: number of results (optional, default: 20)
    """
    try:
        query = request.args.get('q')
        if not query:
            return jsonify({
                'error': 'Missing search query parameter: q',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        limit = int(request.args.get('limit', 20))
        
        resources = learning_service.search_learning_resources(query, limit)
        
        return jsonify({
            'query': query,
            'resources': resources,
            'count': len(resources)
        }), 200
        
    except Exception as e:
        logger.error(f"Search learning resources error: {str(e)}")
        return jsonify({
            'error': 'Failed to search learning resources',
            'code': 'SEARCH_RESOURCES_ERROR'
        }), 500

@learning_bp.route('/category/<category>', methods=['GET'])
@auth_required
def get_resources_by_category(category):
    """
    Get learning resources by skill category
    Query params:
    - limit: number of results (optional, default: 50)
    """
    try:
        limit = int(request.args.get('limit', 50))
        
        resources = learning_service.get_resources_by_category(category, limit)
        
        return jsonify({
            'category': category,
            'resources': resources,
            'count': len(resources)
        }), 200
        
    except Exception as e:
        logger.error(f"Get resources by category error: {str(e)}")
        return jsonify({
            'error': 'Failed to get resources by category',
            'code': 'GET_CATEGORY_RESOURCES_ERROR'
        }), 500

@learning_bp.route('/complete', methods=['POST'])
@auth_required
def mark_resource_completed():
    """
    Mark a learning resource as completed
    Expected payload: {
        "resourceId": "string",
        "skillId": "string"
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Validate required fields
        if not validate_required_fields(data, ['resourceId', 'skillId']):
            return jsonify({
                'error': 'Missing required fields: resourceId, skillId',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        resource_id = data['resourceId']
        skill_id = data['skillId']
        
        success = learning_service.mark_resource_completed(uid, resource_id, skill_id)
        
        if not success:
            return jsonify({
                'error': 'Failed to mark resource as completed',
                'code': 'MARK_COMPLETED_FAILED'
            }), 500
        
        return jsonify({
            'message': 'Resource marked as completed successfully',
            'resourceId': resource_id,
            'skillId': skill_id
        }), 200
        
    except Exception as e:
        logger.error(f"Mark resource completed error: {str(e)}")
        return jsonify({
            'error': 'Failed to mark resource as completed',
            'code': 'MARK_COMPLETED_ERROR'
        }), 500

@learning_bp.route('/completions', methods=['GET'])
@auth_required
def get_user_completions():
    """
    Get user's completed learning resources
    Query params:
    - skillId: filter by skill (optional)
    """
    try:
        uid = request.current_user['uid']
        skill_id = request.args.get('skillId')
        
        completions = learning_service.get_user_completions(uid, skill_id)
        
        return jsonify({
            'completions': completions,
            'count': len(completions),
            'filters': {
                'skillId': skill_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get user completions error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user completions',
            'code': 'GET_COMPLETIONS_ERROR'
        }), 500

@learning_bp.route('/stats', methods=['GET'])
@auth_required
def get_learning_stats():
    """Get user's learning statistics"""
    try:
        uid = request.current_user['uid']
        
        stats = learning_service.get_learning_stats(uid)
        
        return jsonify({
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Get learning stats error: {str(e)}")
        return jsonify({
            'error': 'Failed to get learning statistics',
            'code': 'GET_LEARNING_STATS_ERROR'
        }), 500

@learning_bp.route('/recommendations', methods=['GET'])
@auth_required
def get_recommended_resources():
    """
    Get recommended learning resources for user
    Query params:
    - limit: number of results (optional, default: 10)
    """
    try:
        uid = request.current_user['uid']
        limit = int(request.args.get('limit', 10))
        
        recommendations = learning_service.get_recommended_resources(uid, limit)
        
        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations)
        }), 200
        
    except Exception as e:
        logger.error(f"Get recommended resources error: {str(e)}")
        return jsonify({
            'error': 'Failed to get recommended resources',
            'code': 'GET_RECOMMENDATIONS_ERROR'
        }), 500