from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.skills_engine import SkillsEngine
from app.services.user_state_manager import UserStateManager
from app.utils.validators import validate_required_fields
import logging

logger = logging.getLogger(__name__)
skills_bp = Blueprint('skills', __name__)
skills_engine = SkillsEngine()
state_manager = UserStateManager()

@skills_bp.route('', methods=['GET'])
@auth_required
def get_skills():
    """
    Get user skills only (requires authentication)
    """
    try:
        uid = request.current_user['uid']
        
        skills = skills_engine.get_user_skills(uid)
        
        # Format user skills for frontend
        formatted_skills = []
        for skill in skills:
            formatted_skill = {
                'id': skill.get('skillId'),
                'name': skill.get('name'),
                'category': skill.get('category'),
                'proficiency': skill.get('userLevel', skill.get('level'))
            }
            formatted_skills.append(formatted_skill)
        
        return jsonify(formatted_skills), 200
            
    except Exception as e:
        logger.error(f"Get user skills error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user skills',
            'code': 'GET_SKILLS_ERROR'
        }), 500

@skills_bp.route('/with-role-analysis', methods=['GET'])
@auth_required
def get_skills_with_role_analysis():
    """
    Get user skills with role matching analysis
    Query params:
    - roleId: target role ID for skill gap analysis
    """
    try:
        uid = request.current_user['uid']
        role_id = request.args.get('roleId')
        
        # Get user skills
        user_skills = skills_engine.get_user_skills(uid)
        
        # Format user skills for frontend
        formatted_skills = []
        for skill in user_skills:
            formatted_skill = {
                'id': skill.get('skillId'),
                'name': skill.get('name'),
                'category': skill.get('category'),
                'proficiency': skill.get('userLevel', skill.get('level')),
                'confidence': skill.get('userConfidence', 'medium')
            }
            formatted_skills.append(formatted_skill)
        
        result = {
            'userSkills': formatted_skills,
            'skillsCount': len(formatted_skills)
        }
        
        # Add role analysis if roleId provided
        if role_id:
            role_analysis = skills_engine.analyze_skills_for_role(uid, role_id)
            result['roleAnalysis'] = role_analysis
        
        return jsonify(result), 200
            
    except Exception as e:
        logger.error(f"Get skills with role analysis error: {str(e)}")
        return jsonify({
            'error': 'Failed to get skills with role analysis',
            'code': 'GET_SKILLS_ROLE_ANALYSIS_ERROR'
        }), 500

@skills_bp.route('/master', methods=['GET'])
@auth_required
def get_master_skills():
    """
    Get master skills catalog (simple version without pagination)
    Query params:
    - category: filter by category
    """
    try:
        uid = request.current_user['uid']
        category = request.args.get('category')
        
        # Get master skills with optional category filtering
        all_skills = skills_engine.get_master_skills(category=category)
        
        # Format skills for frontend
        formatted_skills = []
        for skill in all_skills:
            formatted_skill = {
                'id': skill.get('skillId'),
                'name': skill.get('name'),
                'category': skill.get('category'),
                'description': skill.get('description', '')
            }
            formatted_skills.append(formatted_skill)
        
        return jsonify(formatted_skills), 200
            
    except Exception as e:
        logger.error(f"Get master skills error: {str(e)}")
        return jsonify({
            'error': 'Failed to get master skills',
            'code': 'GET_MASTER_SKILLS_ERROR'
        }), 500

@skills_bp.route('/master/paginated', methods=['GET'])
@auth_required
def get_master_skills_paginated():
    """
    Get master skills catalog with pagination and search
    Query params:
    - page: page number (default: 1)
    - limit: items per page (default: 20)
    - category: filter by category
    - search: search query
    - exclude_user_skills: exclude skills user already has (default: true)
    """
    try:
        uid = request.current_user['uid']
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        search = request.args.get('search')
        exclude_user_skills = request.args.get('exclude_user_skills', 'true').lower() == 'true'
        
        # Get user skills if we need to exclude them
        user_skill_ids = set()
        if exclude_user_skills:
            user_skills = skills_engine.get_user_skills(uid)
            user_skill_ids = {skill.get('skillId') for skill in user_skills}
        
        # Get master skills with filtering
        if search:
            all_skills = skills_engine.search_skills(search, limit=1000)  # Get more for filtering
        else:
            all_skills = skills_engine.get_master_skills(category=category)
        
        # Filter out user skills if requested
        if exclude_user_skills:
            all_skills = [skill for skill in all_skills if skill.get('skillId') not in user_skill_ids]
        
        # Paginate
        total_count = len(all_skills)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_skills = all_skills[start_idx:end_idx]
        
        # Format skills for frontend
        formatted_skills = []
        for skill in paginated_skills:
            formatted_skill = {
                'id': skill.get('skillId'),
                'name': skill.get('name'),
                'category': skill.get('category'),
                'description': skill.get('description', '')
            }
            formatted_skills.append(formatted_skill)
        
        return jsonify({
            'skills': formatted_skills,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'totalPages': (total_count + limit - 1) // limit,
                'hasNext': end_idx < total_count,
                'hasPrev': page > 1
            }
        }), 200
            
    except Exception as e:
        logger.error(f"Get paginated master skills error: {str(e)}")
        return jsonify({
            'error': 'Failed to get master skills',
            'code': 'GET_MASTER_SKILLS_PAGINATED_ERROR'
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
        
        # Debug logging
        logger.info(f"Add skill request - UID: {uid}, Data: {data}")
        
        # Validate required fields
        if not validate_required_fields(data, ['skillId', 'level']):
            logger.error(f"Missing required fields in data: {data}")
            return jsonify({
                'error': 'Missing required fields: skillId, level',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        skill_id = data['skillId']
        level = data['level']
        confidence = data.get('confidence', 'medium')
        
        logger.info(f"Parsed values - skillId: '{skill_id}', level: '{level}', confidence: '{confidence}'")
        
        # Validate level
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if level not in valid_levels:
            logger.error(f"Invalid level '{level}' not in {valid_levels}")
            return jsonify({
                'error': f'Invalid level. Must be one of: {", ".join(valid_levels)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Validate confidence
        valid_confidence = ['low', 'medium', 'high']
        if confidence not in valid_confidence:
            logger.error(f"Invalid confidence '{confidence}' not in {valid_confidence}")
            return jsonify({
                'error': f'Invalid confidence. Must be one of: {", ".join(valid_confidence)}',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Check if skill exists in master catalog before calling skills_engine
        from app.db.firestore import FirestoreService
        db_service = FirestoreService()
        master_skill = db_service.get_document('skills_master', skill_id)
        
        if not master_skill:
            logger.error(f"Skill '{skill_id}' not found in skills_master collection")
            return jsonify({
                'error': f'Skill "{skill_id}" not found in master catalog',
                'code': 'SKILL_NOT_FOUND'
            }), 400
        
        logger.info(f"Master skill found: {master_skill.get('name')} (ID: {skill_id})")
        
        # Add skill
        success = skills_engine.add_user_skill(uid, skill_id, level, confidence)
        if not success:
            logger.error(f"skills_engine.add_user_skill returned False for skill '{skill_id}'")
            return jsonify({
                'error': 'Failed to add skill. Skill may already be added.',
                'code': 'ADD_SKILL_FAILED'
            }), 400
        
        # Update user state with new skills
        success_sync = state_manager.sync_user_state_with_database(uid)
        if not success_sync:
            logger.warning(f"Failed to sync user state after adding skill for user {uid}")
        
        logger.info(f"Successfully added skill '{skill_id}' for user {uid}")
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
        
        # Update user state with updated skills
        success_sync = state_manager.sync_user_state_with_database(uid)
        if not success_sync:
            logger.warning(f"Failed to sync user state after updating skill for user {uid}")
        
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
        
        # Sync user state with database after skill removal
        success_sync = state_manager.sync_user_state_with_database(uid)
        if not success_sync:
            logger.warning(f"Failed to sync user state after removing skill for user {uid}")
        
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
    """Analyze skill gaps for a target role with progress tracking"""
    try:
        uid = request.current_user['uid']
        
        # Import analysis tracker
        from app.services.analysis_tracker import AnalysisTracker
        analysis_tracker = AnalysisTracker()
        
        # Check if we have existing analysis with progress
        existing_analysis = analysis_tracker.get_analysis_with_progress(uid, role_id)
        
        if existing_analysis:
            # Return existing analysis with progress data
            return jsonify({
                'roleId': role_id,
                'analysis': existing_analysis['analysis'],
                'progress': existing_analysis['progress'],
                'hasProgress': True
            }), 200
        
        # No existing analysis, create new one
        analysis = skills_engine.analyze_skill_gaps(uid, role_id)
        
        if 'error' in analysis:
            return jsonify({
                'error': analysis['error'],
                'code': 'ANALYSIS_FAILED'
            }), 400
        
        # Create initial analysis record
        analysis_id = analysis_tracker.create_initial_analysis(uid, role_id, analysis)
        
        if analysis_id:
            logger.info(f"Created initial analysis record {analysis_id} for user {uid}, role {role_id}")
        
        # Save analysis to user state
        state_manager.update_analysis_data(uid, analysis)
        
        return jsonify({
            'roleId': role_id,
            'analysis': analysis,
            'progress': {
                'initialScore': analysis.get('readinessScore', 0),
                'currentScore': analysis.get('readinessScore', 0),
                'scoreImprovement': 0,
                'initialMatchedSkills': len(analysis.get('matchedSkills', [])),
                'currentMatchedSkills': len(analysis.get('matchedSkills', [])),
                'skillsImprovement': 0,
                'completedRoadmapItems': 0,
                'progressHistory': [],
                'lastUpdated': None,
                'createdAt': None
            },
            'hasProgress': False
        }), 200
        
    except Exception as e:
        logger.error(f"Analyze skill gaps error: {str(e)}")
        return jsonify({
            'error': 'Failed to analyze skill gaps',
            'code': 'ANALYZE_GAPS_ERROR'
        }), 500