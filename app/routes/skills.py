from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.skills_engine import SkillsEngine
from app.utils.validators import validate_required_fields
import logging

logger = logging.getLogger(__name__)
skills_bp = Blueprint('skills', __name__)
skills_engine = SkillsEngine()

@skills_bp.route('', methods=['GET'])
@auth_required
def get_skills():
    """
    Get skills - either master catalog or user skills
    Query params:
    - type: 'master' or 'user' (default: 'user')
    - category: filter by category (for master skills)
    - search: search query (for master skills)
    """
    try:
        uid = request.current_user['uid']
        skill_type = request.args.get('type', 'user')
        category = request.args.get('category')
        search = request.args.get('search')
        
        if skill_type == 'master':
            if search:
                skills = skills_engine.search_skills(search)
            else:
                skills = skills_engine.get_master_skills(category=category)
            
            return jsonify({
                'skills': skills,
                'type': 'master'
            }), 200
        
        else:  # user skills
            skills = skills_engine.get_user_skills(uid)
            
            return jsonify({
                'skills': skills,
                'type': 'user'
            }), 200
            
    except Exception as e:
        logger.error(f"Get skills error: {str(e)}")
        return jsonify({
            'error': 'Failed to get skills',
            'code': 'GET_SKILLS_ERROR'
        }), 500

@skills_bp.route('', methods=['POST'])
@auth_required
def add_skill():
    """
    Add a skill to user's profile
    Expected payload: {
        "skillId": "string",
        "level": "beginner|intermediate|advanced",
        "confidence": "low|medium|high" (optional)
    }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        # Validate required fields
        if not validate_required_fields(data, ['skillId', 'level']):
            return jsonify({
                'error': 'Missing required fields: skillId, level',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        skill_id = data['skillId']
        level = data['level']
        confidence = data.get('confidence', 'medium')
        
        # Validate level
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if level not in valid_levels:
            return jsonify({
                'error': f'Invalid level. Must be one of: {", ".join(valid_levels)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate confidence
        valid_confidence = ['low', 'medium', 'high']
        if confidence not in valid_confidence:
            return jsonify({
                'error': f'Invalid confidence. Must be one of: {", ".join(valid_confidence)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Add skill
        success = skills_engine.add_user_skill(uid, skill_id, level, confidence)
        if not success:
            return jsonify({
                'error': 'Failed to add skill. Skill may not exist or already added.',
                'code': 'ADD_SKILL_FAILED'
            }), 400
        
        return jsonify({
            'message': 'Skill added successfully',
            'skillId': skill_id,
            'level': level,
            'confidence': confidence
        }), 201
        
    except Exception as e:
        logger.error(f"Add skill error: {str(e)}")
        return jsonify({
            'error': 'Failed to add skill',
            'code': 'ADD_SKILL_ERROR'
        }), 500

@skills_bp.route('/<skill_id>', methods=['PUT'])
@auth_required
def update_skill(skill_id):
    """
    Update a user's skill level or confidence
    Expected payload: {
        "level": "beginner|intermediate|advanced" (optional),
        "confidence": "low|medium|high" (optional)
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
        
        level = data.get('level')
        confidence = data.get('confidence')
        
        # Validate level if provided
        if level:
            valid_levels = ['beginner', 'intermediate', 'advanced']
            if level not in valid_levels:
                return jsonify({
                    'error': f'Invalid level. Must be one of: {", ".join(valid_levels)}',
                    'code': 'VALIDATION_ERROR'
                }), 400
        
        # Validate confidence if provided
        if confidence:
            valid_confidence = ['low', 'medium', 'high']
            if confidence not in valid_confidence:
                return jsonify({
                    'error': f'Invalid confidence. Must be one of: {", ".join(valid_confidence)}',
                    'code': 'VALIDATION_ERROR'
                }), 400
        
        if not level and not confidence:
            return jsonify({
                'error': 'At least one field (level or confidence) must be provided',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Update skill
        success = skills_engine.update_user_skill(uid, skill_id, level, confidence)
        if not success:
            return jsonify({
                'error': 'Failed to update skill. Skill may not exist in user profile.',
                'code': 'UPDATE_SKILL_FAILED'
            }), 400
        
        return jsonify({
            'message': 'Skill updated successfully',
            'skillId': skill_id,
            'updates': {k: v for k, v in {'level': level, 'confidence': confidence}.items() if v}
        }), 200
        
    except Exception as e:
        logger.error(f"Update skill error: {str(e)}")
        return jsonify({
            'error': 'Failed to update skill',
            'code': 'UPDATE_SKILL_ERROR'
        }), 500

@skills_bp.route('/<skill_id>', methods=['DELETE'])
@auth_required
def remove_skill(skill_id):
    """Remove a skill from user's profile"""
    try:
        uid = request.current_user['uid']
        
        success = skills_engine.remove_user_skill(uid, skill_id)
        if not success:
            return jsonify({
                'error': 'Failed to remove skill. Skill may not exist in user profile.',
                'code': 'REMOVE_SKILL_FAILED'
            }), 400
        
        return jsonify({
            'message': 'Skill removed successfully',
            'skillId': skill_id
        }), 200
        
    except Exception as e:
        logger.error(f"Remove skill error: {str(e)}")
        return jsonify({
            'error': 'Failed to remove skill',
            'code': 'REMOVE_SKILL_ERROR'
        }), 500

@skills_bp.route('/categories', methods=['GET'])
@auth_required
def get_skill_categories():
    """Get all available skill categories"""
    try:
        categories = skills_engine.get_skill_categories()
        
        return jsonify({
            'categories': categories
        }), 200
        
    except Exception as e:
        logger.error(f"Get skill categories error: {str(e)}")
        return jsonify({
            'error': 'Failed to get skill categories',
            'code': 'GET_CATEGORIES_ERROR'
        }), 500

@skills_bp.route('/<skill_id>/related', methods=['GET'])
@auth_required
def get_related_skills(skill_id):
    """Get skills related to a specific skill"""
    try:
        related_skills = skills_engine.get_related_skills(skill_id)
        
        return jsonify({
            'skillId': skill_id,
            'relatedSkills': related_skills
        }), 200
        
    except Exception as e:
        logger.error(f"Get related skills error: {str(e)}")
        return jsonify({
            'error': 'Failed to get related skills',
            'code': 'GET_RELATED_SKILLS_ERROR'
        }), 500

@skills_bp.route('/analyze/<role_id>', methods=['GET'])
@auth_required
def analyze_skill_gaps(role_id):
    """Analyze skill gaps for a target role"""
    try:
        uid = request.current_user['uid']
        
        analysis = skills_engine.analyze_skill_gaps(uid, role_id)
        
        if 'error' in analysis:
            return jsonify({
                'error': analysis['error'],
                'code': 'ANALYSIS_FAILED'
            }), 400
        
        return jsonify({
            'roleId': role_id,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Analyze skill gaps error: {str(e)}")
        return jsonify({
            'error': 'Failed to analyze skill gaps',
            'code': 'ANALYZE_GAPS_ERROR'
        }), 500