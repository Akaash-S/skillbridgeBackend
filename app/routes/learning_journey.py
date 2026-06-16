import logging
from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.learning_service import LearningService
from app.services.module_service import ModuleService
from app.services.quiz_service import QuizService
from app.services.streak_service import StreakService
from app.services.xp_service import XPService
from app.services.achievement_service import AchievementService
from app.utils.validators import validate_required_fields

logger = logging.getLogger(__name__)
learning_journey_bp = Blueprint('learning_journey', __name__)

learning_service = LearningService()
module_service = ModuleService()
quiz_service = QuizService()
streak_service = StreakService()
xp_service = XPService()
achievement_service = AchievementService()

@learning_journey_bp.route('/learning-mode', methods=['POST'])
@auth_required
def set_learning_mode():
    """
    Set user's learning preference mode
    Expected payload: { "learningMode": "video"|"documentation"|"mixed" }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['learningMode']):
            return jsonify({
                'error': 'Missing required field: learningMode',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        learning_mode = data['learningMode']
        if learning_mode not in ['video', 'documentation', 'mixed']:
            return jsonify({
                'error': 'Invalid learningMode. Must be video, documentation, or mixed',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        success = learning_service.set_learning_mode(uid, learning_mode)
        if not success:
            return jsonify({
                'error': 'Failed to save learning mode',
                'code': 'SAVE_FAILED'
            }), 500
            
        return jsonify({
            'message': 'Learning mode updated successfully',
            'learningMode': learning_mode
        }), 200
        
    except Exception as e:
        logger.error(f"Set learning mode error: {str(e)}")
        return jsonify({
            'error': 'Failed to set learning mode',
            'code': 'SET_LEARNING_MODE_ERROR'
        }), 500

@learning_journey_bp.route('/module', methods=['GET'])
@auth_required
def get_modules():
    """Get or initialize active modules for the user's roadmap"""
    try:
        uid = request.current_user['uid']
        modules = module_service.get_or_initialize_modules(uid)
        return jsonify({
            'modules': modules
        }), 200
    except Exception as e:
        logger.error(f"Get modules error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve modules',
            'code': 'GET_MODULES_ERROR'
        }), 500

@learning_journey_bp.route('/module/start', methods=['POST'])
@auth_required
def start_module():
    """
    Mark a module's learning phase as started (records start timestamp)
    Expected payload: { "moduleIndex": number }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['moduleIndex']):
            return jsonify({
                'error': 'Missing required field: moduleIndex',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        try:
            module_index = int(data['moduleIndex'])
        except (ValueError, TypeError):
            return jsonify({
                'error': 'moduleIndex must be a valid number',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        success = module_service.start_module(uid, module_index)
        if not success:
            return jsonify({
                'error': 'Failed to start module tracking',
                'code': 'START_FAILED'
            }), 500
            
        return jsonify({
            'message': 'Module tracking started successfully',
            'moduleIndex': module_index
        }), 200
    except Exception as e:
        logger.error(f"Start module error: {str(e)}")
        return jsonify({
            'error': 'Failed to start module tracking',
            'code': 'START_MODULE_ERROR'
        }), 500

@learning_journey_bp.route('/module/complete', methods=['POST'])
@auth_required
def complete_module():
    """
    Mark a module's learning phase as completed
    Expected payload: { "moduleIndex": number }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['moduleIndex']):
            return jsonify({
                'error': 'Missing required field: moduleIndex',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        try:
            module_index = int(data['moduleIndex'])
        except (ValueError, TypeError):
            return jsonify({
                'error': 'moduleIndex must be a valid number',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        success = module_service.complete_module(uid, module_index)
        if not success:
            return jsonify({
                'error': 'Failed to complete module',
                'code': 'COMPLETE_FAILED'
            }), 500
        
        # --- Gamification hooks ---
        try:
            streak_data = streak_service.record_activity(uid, 'module')
            xp_data = xp_service.award_xp(uid, 'module_completed')
            new_achievements = achievement_service.check_achievements(uid)
        except Exception as gam_err:
            logger.warning(f"Gamification hook error (non-blocking): {gam_err}")
            streak_data = {}
            xp_data = {}
            new_achievements = []
            
        return jsonify({
            'message': 'Module marked as completed successfully',
            'moduleIndex': module_index,
            'gamification': {
                'streak': streak_data,
                'xp': xp_data,
                'newAchievements': new_achievements
            }
        }), 200
    except Exception as e:
        logger.error(f"Complete module error: {str(e)}")
        return jsonify({
            'error': 'Failed to complete module',
            'code': 'COMPLETE_MODULE_ERROR'
        }), 500

@learning_journey_bp.route('/module-quiz', methods=['GET'])
@auth_required
def get_module_quiz():
    """
    Get 5 multiple choice questions for a specific module
    Query params: ?moduleIndex=number
    """
    try:
        uid = request.current_user['uid']
        module_idx_str = request.args.get('moduleIndex')
        if module_idx_str is None:
            return jsonify({
                'error': 'Missing query parameter: moduleIndex',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        try:
            module_index = int(module_idx_str)
        except ValueError:
            return jsonify({
                'error': 'moduleIndex must be a valid integer',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        # Verify the module is unlocked first
        modules = module_service.get_or_initialize_modules(uid)
        if not modules or module_index < 0 or module_index >= len(modules):
            return jsonify({
                'error': 'Module index out of range',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        module = modules[module_index]
        if not module.get('unlocked', False):
            return jsonify({
                'error': 'This module is locked',
                'code': 'MODULE_LOCKED'
            }), 403
            
        # Generate the quiz questions based on the skills in the module
        skills = module.get('skills', [])
        questions = quiz_service.generate_quiz(skills, module_index)
        
        return jsonify({
            'moduleIndex': module_index,
            'questions': questions
        }), 200
        
    except Exception as e:
        logger.error(f"Get module quiz error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate quiz',
            'code': 'GET_QUIZ_ERROR'
        }), 500

@learning_journey_bp.route('/module-quiz/submit', methods=['POST'])
@auth_required
def submit_module_quiz():
    """
    Submit answers for a module quiz
    Expected payload: { "moduleIndex": number, "answers": { "question_id": selected_idx } }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not validate_required_fields(data, ['moduleIndex', 'answers']):
            return jsonify({
                'error': 'Missing required fields: moduleIndex, answers',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        try:
            module_index = int(data['moduleIndex'])
        except (ValueError, TypeError):
            return jsonify({
                'error': 'moduleIndex must be a valid number',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        answers = data['answers']
        if not isinstance(answers, dict):
            return jsonify({
                'error': 'answers must be a dictionary mapping question IDs to selected option indexes',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        # Grade the quiz
        result = quiz_service.grade_quiz(uid, module_index, answers)
        
        # If passed, update module status to quizPassed = True and unlock next module
        if result.get('passed', False):
            module_service.pass_module_quiz(uid, module_index)
            
            # --- Gamification hooks ---
            try:
                streak_data = streak_service.record_activity(uid, 'quiz')
                xp_data = xp_service.award_xp(uid, 'quiz_passed')
                
                # Check for perfect score
                score = result.get('score', 0)
                total = result.get('total', 1)
                if score == total and total > 0:
                    xp_service.record_perfect_quiz(uid)
                
                new_achievements = achievement_service.check_achievements(uid)
                result['gamification'] = {
                    'streak': streak_data,
                    'xp': xp_data,
                    'newAchievements': new_achievements
                }
            except Exception as gam_err:
                logger.warning(f"Gamification hook error (non-blocking): {gam_err}")
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Submit module quiz error: {str(e)}")
        return jsonify({
            'error': 'Failed to submit quiz',
            'code': 'SUBMIT_QUIZ_ERROR'
        }), 500
