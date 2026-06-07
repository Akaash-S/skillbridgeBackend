from app.db.firestore import FirestoreService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

GAMIFICATION_COLLECTION = 'users'

# Achievement definitions
ACHIEVEMENT_DEFS = [
    {
        'id': 'first_module',
        'title': 'First Steps',
        'description': 'Complete your first learning module',
        'icon': '📘',
        'condition': lambda stats: stats.get('modulesCompleted', 0) >= 1
    },
    {
        'id': 'first_quiz',
        'title': 'Quiz Whiz',
        'description': 'Pass your first micro quiz',
        'icon': '✅',
        'condition': lambda stats: stats.get('quizzesCompleted', 0) >= 1
    },
    {
        'id': 'streak_7',
        'title': 'Week Warrior',
        'description': 'Maintain a 7-day learning streak',
        'icon': '🔥',
        'condition': lambda stats: stats.get('bestStreak', 0) >= 7
    },
    {
        'id': 'streak_30',
        'title': 'Monthly Marathoner',
        'description': 'Maintain a 30-day learning streak',
        'icon': '🏅',
        'condition': lambda stats: stats.get('bestStreak', 0) >= 30
    },
    {
        'id': 'first_roadmap',
        'title': 'Pathfinder',
        'description': 'Complete your first learning roadmap',
        'icon': '🗺️',
        'condition': lambda stats: stats.get('roadmapsCompleted', 0) >= 1
    },
    {
        'id': 'perfect_quiz',
        'title': 'Perfect Score',
        'description': 'Score 100% on any quiz',
        'icon': '💯',
        'condition': lambda stats: stats.get('perfectQuizzes', 0) >= 1
    },
    {
        'id': 'roadmap_master',
        'title': 'Roadmap Master',
        'description': 'Complete 3 learning roadmaps',
        'icon': '👑',
        'condition': lambda stats: stats.get('roadmapsCompleted', 0) >= 3
    },
    {
        'id': 'xp_1000',
        'title': 'XP Hunter',
        'description': 'Earn 1,000 XP',
        'icon': '⚡',
        'condition': lambda stats: stats.get('totalXP', 0) >= 1000
    },
    {
        'id': 'xp_5000',
        'title': 'XP Legend',
        'description': 'Earn 5,000 XP',
        'icon': '🌟',
        'condition': lambda stats: stats.get('totalXP', 0) >= 5000
    },
    {
        'id': 'modules_5',
        'title': 'Dedicated Learner',
        'description': 'Complete 5 learning modules',
        'icon': '📚',
        'condition': lambda stats: stats.get('modulesCompleted', 0) >= 5
    },
    {
        'id': 'quizzes_10',
        'title': 'Quiz Champion',
        'description': 'Pass 10 micro quizzes',
        'icon': '🏆',
        'condition': lambda stats: stats.get('quizzesCompleted', 0) >= 10
    },
]


class AchievementService:
    """Checks and unlocks achievements based on user progress."""

    def __init__(self):
        self.db = FirestoreService()

    def _get_gamification_doc(self, uid: str) -> dict:
        """Get or initialize the gamification document for a user."""
        doc = self.db.get_document(GAMIFICATION_COLLECTION, f"{uid}/gamification/data")
        if not doc:
            from app.services.streak_service import StreakService
            doc = StreakService()._initialize_gamification(uid)
        return doc

    def check_achievements(self, uid: str) -> list:
        """
        Check all achievement conditions against current user stats.
        Unlocks any newly qualified achievements.
        
        Returns:
            List of newly unlocked achievement dicts
        """
        try:
            doc = self._get_gamification_doc(uid)
            existing = doc.get('achievements', {})
            newly_unlocked = []

            for achievement in ACHIEVEMENT_DEFS:
                aid = achievement['id']

                # Skip already unlocked
                if aid in existing and existing[aid].get('unlocked', False):
                    continue

                # Check condition
                if achievement['condition'](doc):
                    existing[aid] = {
                        'unlocked': True,
                        'unlockedAt': datetime.utcnow().isoformat()
                    }
                    newly_unlocked.append({
                        'id': aid,
                        'title': achievement['title'],
                        'description': achievement['description'],
                        'icon': achievement['icon'],
                        'unlockedAt': existing[aid]['unlockedAt']
                    })
                    logger.info(f"🏆 Achievement unlocked for {uid}: {achievement['title']}")

            # Persist if any new unlocks
            if newly_unlocked:
                self.db.update_document(
                    GAMIFICATION_COLLECTION,
                    f"{uid}/gamification/data",
                    {'achievements': existing},
                    create_if_missing=True
                )

            return newly_unlocked

        except Exception as e:
            logger.error(f"❌ Error checking achievements for {uid}: {str(e)}")
            return []

    def get_achievements(self, uid: str) -> list:
        """
        Get all achievements with unlock status for a user.
        
        Returns:
            List of all achievement dicts with unlocked/locked status
        """
        try:
            doc = self._get_gamification_doc(uid)
            existing = doc.get('achievements', {})

            result = []
            for achievement in ACHIEVEMENT_DEFS:
                aid = achievement['id']
                unlocked_data = existing.get(aid, {})
                result.append({
                    'id': aid,
                    'title': achievement['title'],
                    'description': achievement['description'],
                    'icon': achievement['icon'],
                    'unlocked': unlocked_data.get('unlocked', False),
                    'unlockedAt': unlocked_data.get('unlockedAt')
                })

            return result

        except Exception as e:
            logger.error(f"❌ Error getting achievements for {uid}: {str(e)}")
            return []
