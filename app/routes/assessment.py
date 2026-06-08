from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.assessment_service import AssessmentService
from app.services.streak_service import StreakService
from app.services.xp_service import XPService
from app.services.achievement_service import AchievementService
from app import limiter
import logging

logger = logging.getLogger(__name__)
assessment_bp = Blueprint('assessment', __name__)
assessment_service = AssessmentService()
streak_service = StreakService()
xp_service = XPService()
achievement_service = AchievementService()

@assessment_bp.route('/eligibility/<role_id>', methods=['GET'])
@auth_required
def check_eligibility(role_id):
    """Check if user is eligible to take the assessment"""
    uid = request.current_user['uid']
    result = assessment_service.check_eligibility(uid, role_id)
    return jsonify(result)

@assessment_bp.route('/questions/<role_id>', methods=['GET'])
@auth_required
def get_questions(role_id):
    """Fetch questions for the assessment"""
    # In a real proctored environment, we might restrict this 
    # to only be callable after a session has started
    questions = assessment_service.get_questions(role_id)
    
    # Hide correct answers in the response to prevent client-side cheating
    # The client only needs the text and options
    safe_questions = []
    for q in questions:
        safe_q = {
            'id': q.get('id'),
            'text': q.get('text'),
            'options': q.get('options')
        }
        safe_questions.append(safe_q)
        
    return jsonify(safe_questions)

@assessment_bp.route('/start', methods=['POST'])
@auth_required
def start_session():
    """Start a new assessment session"""
    uid = request.current_user['uid']
    data = request.get_json()
    role_id = data.get('roleId')
    
    if not role_id:
        return jsonify({'error': 'roleId is required'}), 400
        
    session_id = assessment_service.start_session(uid, role_id)
    if session_id:
        return jsonify({'sessionId': session_id, 'status': 'active'})
    return jsonify({'error': 'Failed to start session'}), 500

@assessment_bp.route('/violation', methods=['POST'])
@auth_required
def log_violation():
    """Log a violation during the test"""
    data = request.get_json()
    session_id = data.get('sessionId')
    violation_type = data.get('type')
    details = data.get('details', '')
    
    if not session_id or not violation_type:
        return jsonify({'error': 'sessionId and type are required'}), 400
        
    result = assessment_service.log_violation(session_id, violation_type, details)
    return jsonify(result)

@assessment_bp.route('/submit', methods=['POST'])
@auth_required
def submit_assessment():
    """Submit assessment answers"""
    data = request.get_json()
    session_id = data.get('sessionId')
    answers = data.get('answers') # Dict of {q_id: answer_text}
    
    if not session_id or not answers:
        return jsonify({'error': 'sessionId and answers are required'}), 400
        
    result = assessment_service.submit_assessment(session_id, answers)
    
    # --- Gamification hooks (only if passed) ---
    if result.get('passed', False):
        try:
            uid = request.current_user['uid']
            streak_data = streak_service.record_activity(uid, 'assessment')
            xp_data = xp_service.award_xp(uid, 'assessment_passed')
            new_achievements = achievement_service.check_achievements(uid)
            result['gamification'] = {
                'streak': streak_data,
                'xp': xp_data,
                'newAchievements': new_achievements
            }
        except Exception as gam_err:
            logger.warning(f"Gamification hook error (non-blocking): {gam_err}")
    
    return jsonify(result)

@assessment_bp.route('/sessions', methods=['GET'])
@auth_required
def get_user_sessions():
    """Get all assessment sessions for the user"""
    try:
        uid = request.current_user['uid']
        sessions = assessment_service.get_user_sessions(uid)
        return jsonify(sessions), 200
    except Exception as e:
        logger.error(f"Error fetching user sessions: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch assessment sessions',
            'code': 'FETCH_ERROR'
        }), 500

@assessment_bp.route('/seed-quiz', methods=['POST'])
@auth_required
@limiter.limit("1 per minute")
def seed_from_quizapi():
    """Endpoint to seed questions from QuizAPI"""
    data = request.get_json() or {}
    role_id = data.get('roleId')
    
    results = assessment_service.seed_from_quizapi(role_id)
    return jsonify({'status': 'success', 'results': results})

@assessment_bp.route('/seed', methods=['POST'])
@auth_required
def seed_questions():
    """Admin endpoint to seed fallback questions"""
    assessment_service.seed_questions()
    return jsonify({'message': 'Questions seeded successfully'})
