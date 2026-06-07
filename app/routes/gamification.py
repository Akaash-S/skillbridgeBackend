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
