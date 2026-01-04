from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.db.firestore import FirestoreService
import logging

logger = logging.getLogger(__name__)
activity_bp = Blueprint('activity', __name__)
db_service = FirestoreService()

@activity_bp.route('', methods=['GET'])
@auth_required
def get_user_activity():
    """
    Get user's activity log
    Query params:
    - limit: number of activities (optional, default: 50, max: 100)
    - type: filter by activity type (optional)
    """
    try:
        uid = request.current_user['uid']
        limit = int(request.args.get('limit', 50))
        activity_type = request.args.get('type')
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({
                'error': 'Limit must be between 1 and 100',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Build filters
        filters = [('uid', '==', uid)]
        if activity_type:
            filters.append(('type', '==', activity_type))
        
        # Get activities
        activities = db_service.query_collection('activity_logs', filters, limit)
        
        # Sort by creation date (most recent first)
        activities.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        return jsonify({
            'activities': activities,
            'count': len(activities),
            'filters': {
                'type': activity_type,
                'limit': limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get user activity error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user activity',
            'code': 'GET_ACTIVITY_ERROR'
        }), 500

@activity_bp.route('/types', methods=['GET'])
@auth_required
def get_activity_types():
    """Get available activity types"""
    try:
        # Predefined activity types used in the system
        activity_types = [
            {
                'type': 'LOGIN',
                'description': 'User login events',
                'category': 'authentication'
            },
            {
                'type': 'REGISTRATION',
                'description': 'User registration',
                'category': 'authentication'
            },
            {
                'type': 'PROFILE_UPDATED',
                'description': 'Profile information updates',
                'category': 'profile'
            },
            {
                'type': 'ONBOARDING_COMPLETED',
                'description': 'Onboarding process completion',
                'category': 'profile'
            },
            {
                'type': 'SKILL_ADDED',
                'description': 'New skill added to profile',
                'category': 'skills'
            },
            {
                'type': 'SKILL_UPDATED',
                'description': 'Skill level or confidence updated',
                'category': 'skills'
            },
            {
                'type': 'SKILL_REMOVED',
                'description': 'Skill removed from profile',
                'category': 'skills'
            },
            {
                'type': 'ROADMAP_GENERATED',
                'description': 'AI roadmap generated',
                'category': 'roadmap'
            },
            {
                'type': 'ROADMAP_PROGRESS',
                'description': 'Roadmap milestone or skill progress',
                'category': 'roadmap'
            },
            {
                'type': 'ROADMAP_RESET',
                'description': 'Roadmap reset by user',
                'category': 'roadmap'
            },
            {
                'type': 'LEARNING_COMPLETED',
                'description': 'Learning resource completed',
                'category': 'learning'
            },
            {
                'type': 'SETTINGS_UPDATED',
                'description': 'User settings updated',
                'category': 'settings'
            }
        ]
        
        return jsonify({
            'activityTypes': activity_types
        }), 200
        
    except Exception as e:
        logger.error(f"Get activity types error: {str(e)}")
        return jsonify({
            'error': 'Failed to get activity types',
            'code': 'GET_ACTIVITY_TYPES_ERROR'
        }), 500

@activity_bp.route('/summary', methods=['GET'])
@auth_required
def get_activity_summary():
    """
    Get user's activity summary (counts by type and recent activity)
    Query params:
    - days: number of days to include (optional, default: 30)
    """
    try:
        uid = request.current_user['uid']
        days = int(request.args.get('days', 30))
        
        # Validate days
        if days < 1 or days > 365:
            return jsonify({
                'error': 'Days must be between 1 and 365',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Get all user activities (we'll filter by date in memory for simplicity)
        all_activities = db_service.get_user_activity(uid, limit=1000)
        
        # Filter by date range (simplified - in production, use Firestore date queries)
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_activities = []
        for activity in all_activities:
            activity_date = activity.get('createdAt')
            if activity_date and activity_date >= cutoff_date:
                recent_activities.append(activity)
        
        # Count activities by type
        activity_counts = {}
        for activity in recent_activities:
            activity_type = activity.get('type', 'UNKNOWN')
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        
        # Get most recent activities
        recent_activities.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        latest_activities = recent_activities[:10]
        
        # Calculate daily activity (simplified)
        daily_counts = {}
        for activity in recent_activities:
            activity_date = activity.get('createdAt')
            if activity_date:
                date_key = activity_date.strftime('%Y-%m-%d')
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        summary = {
            'totalActivities': len(recent_activities),
            'activityCounts': activity_counts,
            'dailyCounts': daily_counts,
            'latestActivities': latest_activities,
            'dateRange': {
                'days': days,
                'from': cutoff_date.isoformat(),
                'to': datetime.utcnow().isoformat()
            }
        }
        
        return jsonify({
            'summary': summary
        }), 200
        
    except Exception as e:
        logger.error(f"Get activity summary error: {str(e)}")
        return jsonify({
            'error': 'Failed to get activity summary',
            'code': 'GET_ACTIVITY_SUMMARY_ERROR'
        }), 500