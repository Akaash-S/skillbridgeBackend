from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required, optional_auth
from app.db.firestore import FirestoreService
import logging

logger = logging.getLogger(__name__)
roles_bp = Blueprint('roles', __name__)
db_service = FirestoreService()

@roles_bp.route('', methods=['GET'])
@optional_auth
def get_job_roles():
    """
    Get all available job roles
    Query params:
    - category: filter by category (optional)
    """
    try:
        category = request.args.get('category')
        
        # Build filters
        filters = []
        if category:
            filters.append(('category', '==', category))
        
        # Get job roles from Firestore
        job_roles = db_service.query_collection('job_roles', filters)
        
        # Format for frontend compatibility
        formatted_roles = []
        for role in job_roles:
            formatted_role = {
                'id': role.get('roleId'),  # Frontend expects 'id'
                'title': role.get('title'),
                'description': role.get('description'),
                'requiredSkills': role.get('requiredSkills', []),
                'category': role.get('category'),
                'avgSalary': role.get('avgSalary'),
                'demand': role.get('demand')
            }
            formatted_roles.append(formatted_role)
        
        return jsonify(formatted_roles), 200
        
    except Exception as e:
        logger.error(f"Get job roles error: {str(e)}")
        return jsonify({
            'error': 'Failed to get job roles',
            'code': 'GET_ROLES_ERROR'
        }), 500

@roles_bp.route('/<role_id>', methods=['GET'])
@optional_auth
def get_job_role(role_id):
    """Get a specific job role by ID"""
    try:
        role = db_service.get_document('job_roles', role_id)
        
        if not role:
            return jsonify({
                'error': 'Job role not found',
                'code': 'ROLE_NOT_FOUND'
            }), 404
        
        # Format for frontend
        formatted_role = {
            'id': role.get('roleId'),
            'title': role.get('title'),
            'description': role.get('description'),
            'requiredSkills': role.get('requiredSkills', []),
            'category': role.get('category'),
            'avgSalary': role.get('avgSalary'),
            'demand': role.get('demand')
        }
        
        return jsonify(formatted_role), 200
        
    except Exception as e:
        logger.error(f"Get job role error: {str(e)}")
        return jsonify({
            'error': 'Failed to get job role',
            'code': 'GET_ROLE_ERROR'
        }), 500

@roles_bp.route('/categories', methods=['GET'])
@optional_auth
def get_role_categories():
    """Get all available role categories"""
    try:
        # Get all roles and extract unique categories
        all_roles = db_service.query_collection('job_roles')
        categories = set()
        
        for role in all_roles:
            category = role.get('category')
            if category:
                categories.add(category)
        
        return jsonify({
            'categories': sorted(list(categories))
        }), 200
        
    except Exception as e:
        logger.error(f"Get role categories error: {str(e)}")
        return jsonify({
            'error': 'Failed to get role categories',
            'code': 'GET_CATEGORIES_ERROR'
        }), 500