from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required, optional_auth
from app.services.user_state_manager import UserStateManager
from app.db.firestore import FirestoreService
import logging

logger = logging.getLogger(__name__)
roles_bp = Blueprint('roles', __name__)
db_service = FirestoreService()
state_manager = UserStateManager()

@roles_bp.route('', methods=['GET'])
@auth_required
def get_job_roles():
    """
    Get all available job roles (requires authentication)
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
            'code': 'GET_JOB_ROLES_ERROR'
        }), 500
        
@roles_bp.route('/with-skill-match', methods=['GET'])
@auth_required
def get_roles_with_skill_match():
    """
    Get job roles with skill matching analysis for the current user
    Query params:
    - category: filter by category (optional)
    - limit: number of roles to return (default: 20)
    """
    try:
        uid = request.current_user['uid']
        category = request.args.get('category')
        limit = int(request.args.get('limit', 20))
        
        # Build filters
        filters = []
        if category:
            filters.append(('category', '==', category))
        
        # Get job roles from Firestore
        job_roles = db_service.query_collection('job_roles', filters)
        
        # Get user skills for matching
        user_skills = db_service.get_user_skills(uid)
        user_skill_map = {skill.get('skillId'): skill.get('level', 'beginner') for skill in user_skills}
        
        # Format roles with skill matching
        formatted_roles = []
        proficiency_values = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        
        for role in job_roles[:limit]:  # Limit results
            required_skills = role.get('requiredSkills', [])
            
            # Calculate skill match percentage
            if required_skills and user_skills:
                matched_count = 0
                partial_count = 0
                
                for req_skill in required_skills:
                    skill_id = req_skill.get('skillId')
                    required_level = req_skill.get('minProficiency', 'intermediate')
                    
                    if skill_id in user_skill_map:
                        user_level = user_skill_map[skill_id]
                        if proficiency_values.get(user_level, 1) >= proficiency_values.get(required_level, 2):
                            matched_count += 1
                        else:
                            partial_count += 1
                
                total_required = len(required_skills)
                match_percentage = ((matched_count + partial_count * 0.5) / total_required * 100) if total_required > 0 else 0
            else:
                match_percentage = 0
                matched_count = 0
                partial_count = 0
                total_required = len(required_skills)
            
            formatted_role = {
                'id': role.get('roleId'),
                'title': role.get('title'),
                'description': role.get('description'),
                'requiredSkills': required_skills,
                'category': role.get('category'),
                'avgSalary': role.get('avgSalary'),
                'demand': role.get('demand'),
                'skillMatch': {
                    'percentage': round(match_percentage, 1),
                    'matched': matched_count,
                    'partial': partial_count,
                    'missing': total_required - matched_count - partial_count,
                    'total': total_required
                }
            }
            formatted_roles.append(formatted_role)
        
        # Sort by skill match percentage (highest first)
        formatted_roles.sort(key=lambda x: x['skillMatch']['percentage'], reverse=True)
        
        return jsonify({
            'roles': formatted_roles,
            'userSkillsCount': len(user_skills)
        }), 200
        
    except Exception as e:
        logger.error(f"Get roles with skill match error: {str(e)}")
        return jsonify({
            'error': 'Failed to get roles with skill matching',
            'code': 'GET_ROLES_SKILL_MATCH_ERROR'
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

@roles_bp.route('/select', methods=['POST'])
@auth_required
def select_target_role():
    """
    Select a target role for the user
    Expected payload: {
        "roleId": "frontend-dev"
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data or 'roleId' not in data:
            return jsonify({
                'error': 'Missing required field: roleId',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        role_id = data['roleId']
        
        # Get the full role data
        role = db_service.get_document('job_roles', role_id)
        if not role:
            return jsonify({
                'error': 'Job role not found',
                'code': 'ROLE_NOT_FOUND'
            }), 404
        
        # Format role data for state
        from datetime import datetime
        role_data = {
            'id': role.get('roleId'),
            'title': role.get('title'),
            'description': role.get('description'),
            'requiredSkills': role.get('requiredSkills', []),
            'category': role.get('category'),
            'avgSalary': role.get('avgSalary'),
            'demand': role.get('demand'),
            'selectedAt': datetime.utcnow()
        }
        
        # Save target role to user state
        success = state_manager.update_target_role(uid, role_data)
        
        if not success:
            return jsonify({
                'error': 'Failed to save target role',
                'code': 'SAVE_TARGET_ROLE_FAILED'
            }), 500
        
        # Sync user state with database to ensure consistency
        sync_success = state_manager.sync_user_state_with_database(uid)
        if not sync_success:
            logger.warning(f"Failed to sync user state after role selection for user {uid}")
        
        return jsonify({
            'message': 'Target role selected successfully',
            'targetRole': role_data
        }), 200
        
    except Exception as e:
        logger.error(f"Select target role error: {str(e)}")
        return jsonify({
            'error': 'Failed to select target role',
            'code': 'SELECT_TARGET_ROLE_ERROR'
        }), 500