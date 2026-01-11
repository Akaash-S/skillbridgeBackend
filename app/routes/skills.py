from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.skills_engine import SkillsEngine
from app.services.user_state_manager import UserStateManager
from app.utils.validators import validate_required_fields
from datetime import datetime
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
            # Try to find by skillId field instead of document ID
            skills = db_service.query_collection('skills_master', [('skillId', '==', skill_id)])
            if skills:
                master_skill = skills[0]
            else:
                # Skill not found - create it on-the-fly for common skills
                common_skills = {
                    'jenkins': {'name': 'Jenkins', 'category': 'DevOps & Cloud'},
                    'git': {'name': 'Git', 'category': 'DevOps & Cloud'},
                    'github': {'name': 'GitHub', 'category': 'DevOps & Cloud'},
                    'gitlab': {'name': 'GitLab', 'category': 'DevOps & Cloud'},
                    'ansible': {'name': 'Ansible', 'category': 'DevOps & Cloud'},
                    'puppet': {'name': 'Puppet', 'category': 'DevOps & Cloud'},
                    'chef': {'name': 'Chef', 'category': 'DevOps & Cloud'},
                    'nginx': {'name': 'Nginx', 'category': 'DevOps & Cloud'},
                    'apache': {'name': 'Apache', 'category': 'DevOps & Cloud'},
                    'linux': {'name': 'Linux', 'category': 'DevOps & Cloud'},
                    'bash': {'name': 'Bash', 'category': 'DevOps & Cloud'},
                    'powershell': {'name': 'PowerShell', 'category': 'DevOps & Cloud'},
                }
                
                if skill_id in common_skills:
                    skill_info = common_skills[skill_id]
                    new_skill_data = {
                        'skillId': skill_id,
                        'name': skill_info['name'],
                        'category': skill_info['category'],
                        'type': 'technical',
                        'aliases': [],
                        'prerequisites': [],
                        'relatedSkills': [],
                        'levels': ['beginner', 'intermediate', 'advanced'],
                        'source': 'auto-created',
                        'createdAt': datetime.utcnow(),
                        'updatedAt': datetime.utcnow()
                    }
                    
                    # Create the skill in master catalog
                    success = db_service.create_document('skills_master', skill_id, new_skill_data)
                    if success:
                        logger.info(f"Auto-created missing skill: {skill_info['name']} ({skill_id})")
                        master_skill = new_skill_data
                    else:
                        logger.error(f"Failed to auto-create skill: {skill_id}")
                        return jsonify({
                            'error': f'Skill "{skill_id}" not found in master catalog and could not be created',
                            'code': 'SKILL_NOT_FOUND'
                        }), 400
                else:
                    logger.error(f"Skill '{skill_id}' not found in skills_master collection and not in common skills list")
                    return jsonify({
                        'error': f'Skill "{skill_id}" not found in master catalog',
                        'code': 'SKILL_NOT_FOUND'
                    }), 400
        
        if not master_skill:
            logger.error(f"Skill '{skill_id}' not found in skills_master collection")
            return jsonify({
                'error': f'Skill "{skill_id}" not found in master catalog',
                'code': 'SKILL_NOT_FOUND'
            }), 400
        
        logger.info(f"Master skill found: {master_skill.get('name')} (ID: {skill_id})")
        
        # Add skill using the skills engine
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

@skills_bp.route('/analytics', methods=['GET'])
@auth_required
def get_skills_analytics():
    """
    Get comprehensive skills analytics and intelligence data
    Returns market demand, salary impact, and skill trends
    """
    try:
        uid = request.current_user['uid']
        
        # Get user skills for personalized analytics
        user_skills = skills_engine.get_user_skills(uid)
        user_skill_ids = [skill.get('skillId') for skill in user_skills]
        
        # Get all master skills for market analysis
        all_skills = skills_engine.get_master_skills()
        
        # Calculate skill analytics
        skill_analytics = {}
        
        for skill in all_skills:
            skill_id = skill.get('skillId')
            skill_name = skill.get('name')
            category = skill.get('category')
            
            # Mock analytics data based on skill popularity and category
            is_hot = skill_id in ['react', 'ts', 'python', 'kubernetes', 'ml', 'aws', 'docker', 'nextjs']
            is_emerging = skill_id in ['rust', 'go', 'graphql', 'webassembly']
            is_declining = skill_id in ['angular', 'java', 'jquery']
            
            # Calculate demand based on category and popularity
            base_demand = {
                'Programming Languages': 75,
                'Frontend': 70,
                'Backend': 72,
                'Database': 65,
                'DevOps & Cloud': 80,
                'Data Science': 85,
                'Soft Skills': 60
            }.get(category, 50)
            
            # Adjust demand based on skill status
            if is_hot:
                demand = min(95, base_demand + 20)
                salary_impact = 15
                growth_rate = 25
            elif is_emerging:
                demand = min(85, base_demand + 10)
                salary_impact = 12
                growth_rate = 35
            elif is_declining:
                demand = max(20, base_demand - 30)
                salary_impact = 3
                growth_rate = -10
            else:
                demand = base_demand
                salary_impact = 8
                growth_rate = 5
            
            skill_analytics[skill_id] = {
                'skillId': skill_id,
                'skillName': skill_name,
                'category': category,
                'demandPercentage': demand,
                'salaryImpact': salary_impact,
                'growthRate': growth_rate,
                'trend': 'up' if growth_rate > 10 else 'down' if growth_rate < 0 else 'stable',
                'isHot': is_hot,
                'isEmerging': is_emerging,
                'isDeclining': is_declining,
                'jobOpenings': max(500, int(demand * 100 + (hash(skill_id) % 5000))),
                'learningTime': '2-4 months' if is_hot else '3-6 months' if is_emerging else '1-3 months',
                'difficulty': 'advanced' if is_emerging else 'intermediate' if is_hot else 'beginner',
                'hasUserSkill': skill_id in user_skill_ids
            }
        
        # Calculate user portfolio analytics
        user_analytics = {
            'totalSkills': len(user_skills),
            'hotSkills': len([s for s in user_skill_ids if skill_analytics.get(s, {}).get('isHot', False)]),
            'emergingSkills': len([s for s in user_skill_ids if skill_analytics.get(s, {}).get('isEmerging', False)]),
            'decliningSkills': len([s for s in user_skill_ids if skill_analytics.get(s, {}).get('isDeclining', False)]),
            'averageDemand': sum([skill_analytics.get(s, {}).get('demandPercentage', 0) for s in user_skill_ids]) / max(len(user_skill_ids), 1),
            'totalSalaryImpact': sum([skill_analytics.get(s, {}).get('salaryImpact', 0) for s in user_skill_ids]),
            'marketValue': 'high' if len([s for s in user_skill_ids if skill_analytics.get(s, {}).get('demandPercentage', 0) > 70]) > len(user_skill_ids) * 0.5 else 'medium'
        }
        
        return jsonify({
            'skillAnalytics': skill_analytics,
            'userAnalytics': user_analytics,
            'marketOverview': {
                'totalSkills': len(all_skills),
                'hotSkills': len([s for s in skill_analytics.values() if s.get('isHot')]),
                'emergingSkills': len([s for s in skill_analytics.values() if s.get('isEmerging')]),
                'decliningSkills': len([s for s in skill_analytics.values() if s.get('isDeclining')]),
                'averageGrowthRate': sum([s.get('growthRate', 0) for s in skill_analytics.values()]) / len(skill_analytics)
            },
            'generatedAt': '2024-01-10T00:00:00Z'
        }), 200
        
    except Exception as e:
        logger.error(f"Get skills analytics error: {str(e)}")
        return jsonify({
            'error': 'Failed to get skills analytics',
            'code': 'GET_ANALYTICS_ERROR'
        }), 500

@skills_bp.route('/market-trends', methods=['GET'])
@auth_required
def get_market_trends():
    """
    Get market trends and forecasting data for skills
    Returns trend analysis, demand forecasts, and market insights
    """
    try:
        uid = request.current_user['uid']
        
        # Get user skills for personalized trends
        user_skills = skills_engine.get_user_skills(uid)
        user_skill_ids = [skill.get('skillId') for skill in user_skills]
        
        # Market trends data
        market_trends = {
            'trendingUp': [
                {'skillId': 'react', 'skillName': 'React', 'growthRate': 28, 'reason': 'High demand for modern web development'},
                {'skillId': 'python', 'skillName': 'Python', 'growthRate': 32, 'reason': 'AI/ML boom and versatility'},
                {'skillId': 'kubernetes', 'skillName': 'Kubernetes', 'growthRate': 45, 'reason': 'Container orchestration adoption'},
                {'skillId': 'aws', 'skillName': 'AWS', 'growthRate': 25, 'reason': 'Cloud-first strategies'},
                {'skillId': 'ml', 'skillName': 'Machine Learning', 'growthRate': 40, 'reason': 'AI revolution across industries'},
                {'skillId': 'ts', 'skillName': 'TypeScript', 'growthRate': 35, 'reason': 'Type safety in JavaScript ecosystem'}
            ],
            'trendingDown': [
                {'skillId': 'angular', 'skillName': 'Angular', 'growthRate': -8, 'reason': 'React dominance in frontend'},
                {'skillId': 'java', 'skillName': 'Java', 'growthRate': -5, 'reason': 'Modern alternatives gaining traction'},
                {'skillId': 'jquery', 'skillName': 'jQuery', 'growthRate': -15, 'reason': 'Modern frameworks replacing legacy code'}
            ],
            'emerging': [
                {'skillId': 'rust', 'skillName': 'Rust', 'growthRate': 55, 'reason': 'System programming and performance'},
                {'skillId': 'go', 'skillName': 'Go', 'growthRate': 42, 'reason': 'Microservices and cloud native development'},
                {'skillId': 'graphql', 'skillName': 'GraphQL', 'growthRate': 38, 'reason': 'API efficiency and flexibility'}
            ],
            'stable': [
                {'skillId': 'js', 'skillName': 'JavaScript', 'growthRate': 8, 'reason': 'Foundational web technology'},
                {'skillId': 'html', 'skillName': 'HTML5', 'growthRate': 5, 'reason': 'Web standard with steady demand'},
                {'skillId': 'css', 'skillName': 'CSS3', 'growthRate': 6, 'reason': 'Essential for web styling'}
            ]
        }
        
        # Industry insights
        industry_insights = {
            'topGrowthSectors': [
                {'sector': 'Artificial Intelligence', 'growthRate': 45, 'keySkills': ['python', 'ml', 'tensorflow', 'pytorch']},
                {'sector': 'Cloud Computing', 'growthRate': 35, 'keySkills': ['aws', 'kubernetes', 'docker', 'terraform']},
                {'sector': 'Web Development', 'growthRate': 25, 'keySkills': ['react', 'ts', 'nextjs', 'nodejs']},
                {'sector': 'Data Science', 'growthRate': 30, 'keySkills': ['python', 'pandas', 'sql', 'dataviz']}
            ],
            'salaryTrends': {
                'highestPaying': [
                    {'skillId': 'ml', 'skillName': 'Machine Learning', 'avgSalaryBoost': 25},
                    {'skillId': 'kubernetes', 'skillName': 'Kubernetes', 'avgSalaryBoost': 22},
                    {'skillId': 'aws', 'skillName': 'AWS', 'avgSalaryBoost': 20},
                    {'skillId': 'python', 'skillName': 'Python', 'avgSalaryBoost': 18}
                ],
                'fastestGrowing': [
                    {'skillId': 'rust', 'skillName': 'Rust', 'salaryGrowth': 35},
                    {'skillId': 'go', 'skillName': 'Go', 'salaryGrowth': 28},
                    {'skillId': 'kubernetes', 'skillName': 'Kubernetes', 'salaryGrowth': 25}
                ]
            },
            'geographicTrends': {
                'hotMarkets': ['San Francisco', 'Seattle', 'New York', 'Austin', 'Boston'],
                'emergingMarkets': ['Denver', 'Atlanta', 'Portland', 'Nashville', 'Raleigh']
            }
        }
        
        # Personalized recommendations based on user skills
        user_recommendations = []
        for skill_id in user_skill_ids:
            # Find complementary skills
            if skill_id == 'react':
                user_recommendations.extend(['ts', 'nextjs', 'nodejs'])
            elif skill_id == 'python':
                user_recommendations.extend(['ml', 'pandas', 'aws'])
            elif skill_id == 'js':
                user_recommendations.extend(['react', 'ts', 'nodejs'])
        
        # Remove duplicates and skills user already has
        user_recommendations = list(set(user_recommendations) - set(user_skill_ids))
        
        # Forecast data (next 12 months)
        forecast = {
            'skillDemandForecast': {
                'increasingDemand': ['python', 'react', 'kubernetes', 'ml', 'aws'],
                'decreasingDemand': ['angular', 'java', 'jquery'],
                'stableDemand': ['js', 'html', 'css', 'sql']
            },
            'jobMarketForecast': {
                'totalJobGrowth': 15,
                'techJobGrowth': 22,
                'remoteJobGrowth': 35,
                'aiRelatedJobGrowth': 50
            },
            'skillGapAnalysis': {
                'mostInDemand': ['python', 'react', 'kubernetes', 'ml'],
                'leastSupplied': ['rust', 'go', 'kubernetes', 'ml'],
                'biggestGaps': ['ml', 'kubernetes', 'rust', 'go']
            }
        }
        
        return jsonify({
            'marketTrends': market_trends,
            'industryInsights': industry_insights,
            'userRecommendations': user_recommendations[:8],  # Limit to top 8
            'forecast': forecast,
            'lastUpdated': '2024-01-10T00:00:00Z',
            'dataSource': 'SkillBridge Intelligence Engine'
        }), 200
        
    except Exception as e:
        logger.error(f"Get market trends error: {str(e)}")
        return jsonify({
            'error': 'Failed to get market trends',
            'code': 'GET_MARKET_TRENDS_ERROR'
        }), 500