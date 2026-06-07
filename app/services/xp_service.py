from app.db.firestore import FirestoreService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

GAMIFICATION_COLLECTION = 'users'

# XP rewards for each action
XP_REWARDS = {
    'module_started': 10,
    'module_completed': 50,
    'quiz_passed': 75,
    'assessment_passed': 300,
    'roadmap_completed': 500,
    'assistant_usage': 5,
}

# Daily cap for AI assistant XP
ASSISTANT_DAILY_CAP = 25

# Level thresholds
LEVELS = [
    {'level': 1, 'title': 'Beginner', 'minXP': 0},
    {'level': 2, 'title': 'Explorer', 'minXP': 200},
    {'level': 3, 'title': 'Builder', 'minXP': 500},
    {'level': 4, 'title': 'Practitioner', 'minXP': 1200},
    {'level': 5, 'title': 'Specialist', 'minXP': 2500},
    {'level': 6, 'title': 'Master', 'minXP': 5000},
]


class XPService:
    """Manages XP accrual, level calculation, and periodic resets."""

    def __init__(self):
        self.db = FirestoreService()

    def _get_gamification_doc(self, uid: str) -> dict:
        """Get or initialize the gamification document for a user."""
        doc = self.db.get_document(GAMIFICATION_COLLECTION, f"{uid}/gamification/data")
        if not doc:
            from app.services.streak_service import StreakService
            doc = StreakService()._initialize_gamification(uid)
        return doc

    @staticmethod
    def _calculate_level(total_xp: int) -> dict:
        """Pure function: map total XP to level and title."""
        current = LEVELS[0]
        next_level = LEVELS[1] if len(LEVELS) > 1 else None

        for i, lvl in enumerate(LEVELS):
            if total_xp >= lvl['minXP']:
                current = lvl
                next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
            else:
                break

        # Calculate progress to next level
        if next_level:
            xp_into_level = total_xp - current['minXP']
            xp_for_next = next_level['minXP'] - current['minXP']
            progress = round((xp_into_level / xp_for_next) * 100, 1) if xp_for_next > 0 else 100
        else:
            progress = 100

        return {
            'level': current['level'],
            'title': current['title'],
            'nextLevel': next_level['level'] if next_level else None,
            'nextTitle': next_level['title'] if next_level else None,
            'nextLevelXP': next_level['minXP'] if next_level else None,
            'currentLevelXP': current['minXP'],
            'progressToNext': progress
        }

    def award_xp(self, uid: str, action: str, amount: int = None) -> dict:
        """
        Award XP for a specific action.
        
        Args:
            uid: User ID
            action: Action type (e.g. 'module_completed', 'quiz_passed')
            amount: Override XP amount (uses default from XP_REWARDS if None)
        
        Returns:
            Updated XP data including whether user leveled up
        """
        try:
            if amount is None:
                amount = XP_REWARDS.get(action, 0)

            if amount <= 0:
                return self.get_xp(uid)

            doc = self._get_gamification_doc(uid)
            today = datetime.utcnow().strftime('%Y-%m-%d')

            # Check assistant daily cap
            if action == 'assistant_usage':
                daily_assistant_xp = doc.get('dailyAssistantXP', 0)
                daily_assistant_date = doc.get('dailyAssistantDate')
                if daily_assistant_date == today:
                    if daily_assistant_xp >= ASSISTANT_DAILY_CAP:
                        logger.info(f"⚡ Assistant XP cap reached for {uid}")
                        return self.get_xp(uid)
                    amount = min(amount, ASSISTANT_DAILY_CAP - daily_assistant_xp)
                else:
                    # New day, reset counter
                    doc['dailyAssistantXP'] = 0

            old_total = doc.get('totalXP', 0)
            new_total = old_total + amount
            old_level_info = self._calculate_level(old_total)
            new_level_info = self._calculate_level(new_total)
            leveled_up = new_level_info['level'] > old_level_info['level']

            # Handle weekly/monthly XP with date-based resets
            week_start = doc.get('weekStart', today)
            month_start = doc.get('monthStart', datetime.utcnow().strftime('%Y-%m'))
            current_month = datetime.utcnow().strftime('%Y-%m')

            weekly_xp = doc.get('weeklyXP', 0)
            monthly_xp = doc.get('monthlyXP', 0)

            # Reset weekly if more than 7 days
            try:
                ws_date = datetime.strptime(week_start, '%Y-%m-%d')
                if (datetime.utcnow() - ws_date).days >= 7:
                    weekly_xp = 0
                    week_start = today
            except (ValueError, TypeError):
                weekly_xp = 0
                week_start = today

            # Reset monthly if new month
            if month_start != current_month:
                monthly_xp = 0
                month_start = current_month

            weekly_xp += amount
            monthly_xp += amount

            # Build update payload
            update_data = {
                'totalXP': new_total,
                'weeklyXP': weekly_xp,
                'monthlyXP': monthly_xp,
                'weekStart': week_start,
                'monthStart': month_start,
                'level': new_level_info['level'],
                'levelTitle': new_level_info['title'],
            }

            # Update assistant daily tracking
            if action == 'assistant_usage':
                update_data['dailyAssistantXP'] = doc.get('dailyAssistantXP', 0) + amount
                update_data['dailyAssistantDate'] = today

            # Update counters based on action type
            if action == 'module_completed':
                update_data['modulesCompleted'] = doc.get('modulesCompleted', 0) + 1
            elif action == 'quiz_passed':
                update_data['quizzesCompleted'] = doc.get('quizzesCompleted', 0) + 1
            elif action == 'roadmap_completed':
                update_data['roadmapsCompleted'] = doc.get('roadmapsCompleted', 0) + 1

            self.db.update_document(
                GAMIFICATION_COLLECTION,
                f"{uid}/gamification/data",
                update_data,
                create_if_missing=True
            )

            result = {
                'totalXP': new_total,
                'weeklyXP': weekly_xp,
                'monthlyXP': monthly_xp,
                'xpAwarded': amount,
                'action': action,
                'level': new_level_info['level'],
                'levelTitle': new_level_info['title'],
                'leveledUp': leveled_up,
                'levelInfo': new_level_info
            }

            emoji = '🎉' if leveled_up else '⚡'
            logger.info(f"{emoji} XP awarded to {uid}: +{amount} ({action}) → Total: {new_total} (Level {new_level_info['level']})")

            return result

        except Exception as e:
            logger.error(f"❌ Error awarding XP to {uid}: {str(e)}")
            return {
                'totalXP': 0, 'weeklyXP': 0, 'monthlyXP': 0,
                'xpAwarded': 0, 'action': action,
                'level': 1, 'levelTitle': 'Beginner',
                'leveledUp': False, 'levelInfo': self._calculate_level(0)
            }

    def get_xp(self, uid: str) -> dict:
        """Get full XP profile for a user."""
        try:
            doc = self._get_gamification_doc(uid)
            total_xp = doc.get('totalXP', 0)
            level_info = self._calculate_level(total_xp)

            return {
                'totalXP': total_xp,
                'weeklyXP': doc.get('weeklyXP', 0),
                'monthlyXP': doc.get('monthlyXP', 0),
                'level': level_info['level'],
                'levelTitle': level_info['title'],
                'levelInfo': level_info,
                'modulesCompleted': doc.get('modulesCompleted', 0),
                'quizzesCompleted': doc.get('quizzesCompleted', 0),
                'roadmapsCompleted': doc.get('roadmapsCompleted', 0),
            }

        except Exception as e:
            logger.error(f"❌ Error getting XP for {uid}: {str(e)}")
            return {
                'totalXP': 0, 'weeklyXP': 0, 'monthlyXP': 0,
                'level': 1, 'levelTitle': 'Beginner',
                'levelInfo': self._calculate_level(0),
                'modulesCompleted': 0, 'quizzesCompleted': 0, 'roadmapsCompleted': 0
            }

    def record_perfect_quiz(self, uid: str) -> None:
        """Increment the perfect quiz counter."""
        try:
            doc = self._get_gamification_doc(uid)
            self.db.update_document(
                GAMIFICATION_COLLECTION,
                f"{uid}/gamification/data",
                {'perfectQuizzes': doc.get('perfectQuizzes', 0) + 1},
                create_if_missing=True
            )
        except Exception as e:
            logger.error(f"❌ Error recording perfect quiz for {uid}: {str(e)}")
