from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.streak_service import StreakService
from app.services.xp_service import XPService
from app.services.achievement_service import AchievementService
from app import limiter
import logging

logger = logging.getLogger(__name__)
gamification_bp = Blueprint('gamification', __name__)

streak_service = StreakService()
xp_service = XPService()
achievement_service = AchievementService()


@gamification_bp.route('/streak', methods=['GET'])
@auth_required
def get_streak():
    """Get current and best streak for the authenticated user."""
    try:
        uid = request.current_user['uid']
        data = streak_service.get_streak(uid)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Get streak error: {str(e)}")
        return jsonify({'error': 'Failed to get streak data', 'code': 'GET_STREAK_ERROR'}), 500


@gamification_bp.route('/xp', methods=['GET'])
@auth_required
def get_xp():
    """Get XP, level, and stats for the authenticated user."""
    try:
        uid = request.current_user['uid']
        data = xp_service.get_xp(uid)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Get XP error: {str(e)}")
        return jsonify({'error': 'Failed to get XP data', 'code': 'GET_XP_ERROR'}), 500


@gamification_bp.route('/achievements', methods=['GET'])
@auth_required
def get_achievements():
    """Get all achievements with unlock status."""
    try:
        uid = request.current_user['uid']
        data = achievement_service.get_achievements(uid)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Get achievements error: {str(e)}")
        return jsonify({'error': 'Failed to get achievements', 'code': 'GET_ACHIEVEMENTS_ERROR'}), 500


@gamification_bp.route('/calendar', methods=['GET'])
@auth_required
def get_calendar():
    """Get learning calendar heatmap data (last 6 months by default)."""
    try:
        uid = request.current_user['uid']
        months = int(request.args.get('months', 6))
        data = streak_service.get_calendar(uid, months)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Get calendar error: {str(e)}")
        return jsonify({'error': 'Failed to get calendar data', 'code': 'GET_CALENDAR_ERROR'}), 500


@gamification_bp.route('/dashboard', methods=['GET'])
@auth_required
def get_motivation_dashboard():
    """
    Aggregated motivation dashboard data.
    Returns streak + xp + achievements + calendar in a single call.
    """
    try:
        uid = request.current_user['uid']

        streak_data = streak_service.get_streak(uid)
        xp_data = xp_service.get_xp(uid)
        achievements = achievement_service.get_achievements(uid)
        calendar = streak_service.get_calendar(uid, 6)

        # Count unlocked achievements
        unlocked_count = sum(1 for a in achievements if a.get('unlocked', False))

        dashboard = {
            'streak': streak_data,
            'xp': xp_data,
            'achievements': achievements,
            'achievementsSummary': {
                'unlocked': unlocked_count,
                'total': len(achievements)
            },
            'calendar': calendar
        }

        return jsonify(dashboard), 200

    except Exception as e:
        logger.error(f"Get motivation dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to get dashboard data', 'code': 'GET_DASHBOARD_ERROR'}), 500

@gamification_bp.route('/sync-legacy', methods=['POST'])
@auth_required
def sync_legacy_progress():
    """Sync legacy roadmap progress into gamification."""
    try:
        uid = request.current_user['uid']
        
        # Check if already synced
        doc = xp_service._get_gamification_doc(uid)
        if doc.get('legacySynced', False):
            return jsonify({'message': 'Already synced', 'synced': True}), 200

        from app.services.module_service import ModuleService
        module_service = ModuleService()
        modules = module_service.get_or_initialize_modules(uid)

        completed_modules = sum(1 for m in modules if m.get('completed', False))
        passed_quizzes = sum(1 for m in modules if m.get('quizPassed', False))

        if completed_modules == 0 and passed_quizzes == 0:
            # Nothing to sync, but mark as synced
            xp_service.db.update_document(
                'users', f"{uid}/gamification/data", 
                {'legacySynced': True}, create_if_missing=True
            )
            return jsonify({'message': 'No legacy progress to sync', 'synced': True}), 200

        # Calculate XP
        from app.services.xp_service import XP_REWARDS
        xp_to_add = (completed_modules * XP_REWARDS.get('module_completed', 50)) + \
                    (passed_quizzes * XP_REWARDS.get('quiz_passed', 75))

        result = xp_service.award_xp(uid, 'legacy_sync', xp_to_add)

        # Update the completed modules and quizzes count so the user sees them
        xp_service.db.update_document(
            'users', f"{uid}/gamification/data", 
            {
                'modulesCompleted': doc.get('modulesCompleted', 0) + completed_modules,
                'quizzesCompleted': doc.get('quizzesCompleted', 0) + passed_quizzes,
                'legacySynced': True
            }, 
            create_if_missing=True
        )

        # Give them at least a 1 day streak
        streak_service.record_activity(uid, 'legacy_sync')

        # Trigger achievement check
        achievement_service.check_achievements(uid)

        return jsonify({'message': 'Legacy progress synced successfully', 'synced': True, 'xpAdded': xp_to_add}), 200

    except Exception as e:
        logger.error(f"Sync legacy progress error: {str(e)}")
        return jsonify({'error': 'Failed to sync legacy progress', 'code': 'SYNC_LEGACY_ERROR'}), 500

