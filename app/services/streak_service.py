from app.db.firestore import FirestoreService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

GAMIFICATION_COLLECTION = 'users'

class StreakService:
    """Manages daily learning streaks for users."""

    def __init__(self):
        self.db = FirestoreService()

    def _get_gamification_doc(self, uid: str) -> dict:
        """Get or initialize the gamification document for a user."""
        doc = self.db.get_document(GAMIFICATION_COLLECTION, f"{uid}/gamification/data")
        if not doc:
            doc = self._initialize_gamification(uid)
        return doc

    def _initialize_gamification(self, uid: str) -> dict:
        """Auto-initialize gamification data for a user (backward compatible)."""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        initial_data = {
            'currentStreak': 0,
            'bestStreak': 0,
            'lastActivityDate': None,
            'totalXP': 0,
            'weeklyXP': 0,
            'monthlyXP': 0,
            'weekStart': today,
            'monthStart': datetime.utcnow().strftime('%Y-%m'),
            'level': 1,
            'levelTitle': 'Beginner',
            'modulesCompleted': 0,
            'quizzesCompleted': 0,
            'roadmapsCompleted': 0,
            'perfectQuizzes': 0,
            'achievements': {},
            'calendar': {},
            'createdAt': datetime.utcnow().isoformat()
        }
        self.db.create_document(GAMIFICATION_COLLECTION, f"{uid}/gamification/data", initial_data)
        logger.info(f"✅ Initialized gamification data for user {uid}")
        return initial_data

    def record_activity(self, uid: str, activity_type: str = 'module') -> dict:
        """
        Record a learning activity for streak tracking.
        Called after module completion, quiz pass, or assessment pass.
        
        Args:
            uid: User ID
            activity_type: Type of activity ('module', 'quiz', 'assessment')
        
        Returns:
            Updated streak data with any changes
        """
        try:
            doc = self._get_gamification_doc(uid)
            today = datetime.utcnow().strftime('%Y-%m-%d')
            last_activity = doc.get('lastActivityDate')
            current_streak = doc.get('currentStreak', 0)
            best_streak = doc.get('bestStreak', 0)
            calendar = doc.get('calendar', {})

            streak_continued = False
            streak_started = False

            if last_activity == today:
                # Already recorded activity today — just update calendar details
                pass
            elif last_activity:
                last_date = datetime.strptime(last_activity, '%Y-%m-%d')
                today_date = datetime.strptime(today, '%Y-%m-%d')
                diff = (today_date - last_date).days

                if diff == 1:
                    # Consecutive day — extend streak
                    current_streak += 1
                    streak_continued = True
                elif diff > 1:
                    # Gap — reset streak
                    current_streak = 1
                    streak_started = True
                # diff == 0 handled above
            else:
                # First ever activity
                current_streak = 1
                streak_started = True

            # Update best streak
            if current_streak > best_streak:
                best_streak = current_streak

            # Update calendar entry
            if today not in calendar:
                calendar[today] = {'activities': 0, 'types': []}
            calendar[today]['activities'] = calendar[today].get('activities', 0) + 1
            if activity_type not in calendar[today].get('types', []):
                calendar[today]['types'] = list(set(calendar[today].get('types', []) + [activity_type]))

            # Persist
            update_data = {
                'currentStreak': current_streak,
                'bestStreak': best_streak,
                'lastActivityDate': today,
                'calendar': calendar
            }
            self.db.update_document(
                GAMIFICATION_COLLECTION,
                f"{uid}/gamification/data",
                update_data,
                create_if_missing=True
            )

            result = {
                'currentStreak': current_streak,
                'bestStreak': best_streak,
                'lastActivityDate': today,
                'streakContinued': streak_continued,
                'streakStarted': streak_started
            }
            logger.info(f"🔥 Streak updated for {uid}: {current_streak} days")
            return result

        except Exception as e:
            logger.error(f"❌ Error recording activity for {uid}: {str(e)}")
            return {
                'currentStreak': 0,
                'bestStreak': 0,
                'lastActivityDate': None,
                'streakContinued': False,
                'streakStarted': False
            }

    def get_streak(self, uid: str) -> dict:
        """
        Get current streak data, checking for staleness.
        If lastActivityDate was before yesterday, streak resets to 0.
        """
        try:
            doc = self._get_gamification_doc(uid)
            current_streak = doc.get('currentStreak', 0)
            best_streak = doc.get('bestStreak', 0)
            last_activity = doc.get('lastActivityDate')

            # Check if streak is stale (no activity yesterday or today)
            if last_activity and current_streak > 0:
                today = datetime.utcnow().strftime('%Y-%m-%d')
                yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                if last_activity != today and last_activity != yesterday:
                    # Streak has lapsed — reset
                    current_streak = 0
                    self.db.update_document(
                        GAMIFICATION_COLLECTION,
                        f"{uid}/gamification/data",
                        {'currentStreak': 0},
                        create_if_missing=True
                    )
                    logger.info(f"🔥 Streak reset for {uid} (last activity: {last_activity})")

            return {
                'currentStreak': current_streak,
                'bestStreak': best_streak,
                'lastActivityDate': last_activity
            }

        except Exception as e:
            logger.error(f"❌ Error getting streak for {uid}: {str(e)}")
            return {'currentStreak': 0, 'bestStreak': 0, 'lastActivityDate': None}

    def get_calendar(self, uid: str, months: int = 6) -> dict:
        """Get learning calendar heatmap data for the last N months."""
        try:
            doc = self._get_gamification_doc(uid)
            calendar = doc.get('calendar', {})

            # Filter to last N months
            cutoff = (datetime.utcnow() - timedelta(days=months * 30)).strftime('%Y-%m-%d')
            filtered = {k: v for k, v in calendar.items() if k >= cutoff}

            return filtered

        except Exception as e:
            logger.error(f"❌ Error getting calendar for {uid}: {str(e)}")
            return {}
