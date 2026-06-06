"""
Learning Assistant Service for SkillBridge

Orchestrates the learning assistant workflow:
- Message processing with context building
- Chat history management in Firestore
- Rate limiting per session
- Suggested prompts generation
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Generator

from app.db.firestore import FirestoreService
from app.services.groq_service import GroqService
from app.config import Config

logger = logging.getLogger(__name__)


class LearningAssistantService:
    """Service that orchestrates the AI Learning Assistant"""

    def __init__(self):
        self.db = FirestoreService()
        self.groq = GroqService()
        self.max_messages_per_session = Config.ASSISTANT_MAX_MESSAGES_PER_SESSION

    def is_available(self) -> bool:
        """Check if the learning assistant is available"""
        return self.groq.is_available()

    def process_message(
        self,
        uid: str,
        message: str,
        context: Dict,
        session_id: Optional[str] = None,
        stream: bool = True,
    ) -> Dict:
        """
        Process a user message and return AI response.

        Args:
            uid: Firebase user ID
            message: User's question
            context: Learning context (role, module, learningMode, etc.)
            session_id: Optional session ID to continue a conversation
            stream: Whether to stream the response

        Returns:
            Dict with 'response' (str or generator), 'sessionId', and metadata
        """
        if not self.is_available():
            return {
                'response': "The AI Learning Assistant is currently unavailable. "
                            "Please check back later or contact support.",
                'sessionId': session_id or '',
                'error': True,
            }

        # Create or retrieve session
        if not session_id:
            session_id = self._create_session(uid, context)

        # Check rate limit
        rate_check = self._enforce_rate_limit(uid, session_id)
        if not rate_check['allowed']:
            return {
                'response': rate_check['reason'],
                'sessionId': session_id,
                'rateLimited': True,
            }

        # Get chat history for context
        history = self._get_session_messages(uid, session_id)

        # Store user message
        self._store_message(uid, session_id, 'user', message)

        # Get AI response
        response = self.groq.chat(
            message=message,
            context=context,
            history=history,
            stream=stream,
        )

        if stream:
            # For streaming, we return the generator and handle storage after
            # The caller is responsible for collecting the full response and
            # calling store_assistant_response() afterward
            return {
                'stream': response,
                'sessionId': session_id,
                'error': False,
            }
        else:
            # For non-streaming, store the response immediately
            self._store_message(uid, session_id, 'assistant', response)
            return {
                'response': response,
                'sessionId': session_id,
                'error': False,
            }

    def store_assistant_response(self, uid: str, session_id: str, content: str):
        """Store an assistant response after streaming completes"""
        self._store_message(uid, session_id, 'assistant', content)

    def get_chat_history(self, uid: str, session_id: Optional[str] = None) -> Dict:
        """
        Get chat history for a user.

        Args:
            uid: Firebase user ID
            session_id: Optional specific session ID

        Returns:
            Dict with session info and messages
        """
        if session_id:
            return self._get_session(uid, session_id)

        # Get the most recent session
        sessions = self._get_recent_sessions(uid, limit=1)
        if sessions:
            return sessions[0]

        return {'messages': [], 'sessionId': None}

    def clear_chat_history(self, uid: str, session_id: Optional[str] = None) -> bool:
        """
        Clear chat history for a user.

        Args:
            uid: Firebase user ID
            session_id: Optional specific session to clear

        Returns:
            True if successful
        """
        try:
            if session_id:
                # Delete specific session
                self.db.delete_document(f'users/{uid}/chat_sessions', session_id)
                logger.info(f"🗑️ Cleared chat session {session_id} for user {uid}")
            else:
                # Delete all sessions for user
                sessions = self.db.query_collection(f'users/{uid}/chat_sessions')
                for session in sessions:
                    sid = session.get('id')
                    if sid:
                        self.db.delete_document(f'users/{uid}/chat_sessions', sid)
                logger.info(f"🗑️ Cleared all chat sessions for user {uid}")

            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear chat history: {str(e)}")
            return False

    def get_suggested_prompts(self, context: Dict) -> List[Dict]:
        """
        Generate contextual suggested prompts based on the user's current state.

        Args:
            context: Learning context with role, module, etc.

        Returns:
            List of suggested prompt objects with label and text
        """
        module = context.get('module', '')
        role = context.get('role', '')
        section = context.get('currentSection', '')

        base_prompts = [
            {
                'label': '💡 Explain Simply',
                'text': f'Explain {module} in simple terms' if module else 'Explain the current topic simply',
            },
            {
                'label': '📝 Give Example',
                'text': f'Give me a practical example of {section or module}' if (section or module) else 'Give me a practical example',
            },
            {
                'label': '📋 Summarize',
                'text': f'Summarize what I need to know about {module}' if module else 'Summarize the current topic',
            },
            {
                'label': '🧠 Quiz Me',
                'text': f'Ask me a practice question about {module}' if module else 'Ask me a practice question',
            },
            {
                'label': '🔄 Revise Topic',
                'text': f'Help me revise the key concepts of {module}' if module else 'Help me revise the key concepts',
            },
        ]

        # Add role-specific prompts
        if role:
            base_prompts.append({
                'label': '🗺️ Roadmap Help',
                'text': f'What should I focus on next in my {role} roadmap?',
            })

        return base_prompts

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _create_session(self, uid: str, context: Dict) -> str:
        """Create a new chat session in Firestore"""
        session_id = str(uuid.uuid4())[:8]  # Short readable ID

        session_data = {
            'role': context.get('role', ''),
            'module': context.get('module', ''),
            'learningMode': context.get('learningMode', 'mixed'),
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow(),
            'messageCount': 0,
            'messages': [],
        }

        try:
            self.db.create_document(
                f'users/{uid}/chat_sessions',
                session_id,
                session_data,
            )
            logger.info(f"📝 Created chat session {session_id} for user {uid}")
        except Exception as e:
            logger.error(f"❌ Failed to create chat session: {str(e)}")

        return session_id

    def _get_session(self, uid: str, session_id: str) -> Dict:
        """Get a specific chat session"""
        try:
            session = self.db.get_document(f'users/{uid}/chat_sessions', session_id)
            if session:
                return {
                    'sessionId': session_id,
                    'messages': session.get('messages', []),
                    'role': session.get('role', ''),
                    'module': session.get('module', ''),
                    'learningMode': session.get('learningMode', ''),
                    'messageCount': session.get('messageCount', 0),
                    'createdAt': str(session.get('createdAt', '')),
                }
            return {'sessionId': session_id, 'messages': []}
        except Exception as e:
            logger.error(f"❌ Failed to get chat session: {str(e)}")
            return {'sessionId': session_id, 'messages': []}

    def _get_recent_sessions(self, uid: str, limit: int = 5) -> List[Dict]:
        """Get recent chat sessions for a user"""
        try:
            sessions = self.db.query_collection(
                f'users/{uid}/chat_sessions',
                limit=limit,
            )
            return [
                {
                    'sessionId': s.get('id', ''),
                    'messages': s.get('messages', []),
                    'role': s.get('role', ''),
                    'module': s.get('module', ''),
                    'messageCount': s.get('messageCount', 0),
                    'createdAt': str(s.get('createdAt', '')),
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"❌ Failed to get recent sessions: {str(e)}")
            return []

    def _get_session_messages(self, uid: str, session_id: str) -> List[Dict]:
        """Get messages from a session for context"""
        try:
            session = self.db.get_document(f'users/{uid}/chat_sessions', session_id)
            if session:
                return session.get('messages', [])
            return []
        except Exception as e:
            logger.error(f"❌ Failed to get session messages: {str(e)}")
            return []

    def _store_message(self, uid: str, session_id: str, role: str, content: str):
        """Store a message in the chat session with 30-message cap"""
        try:
            session = self.db.get_document(f'users/{uid}/chat_sessions', session_id)
            if not session:
                # Session doesn't exist, create it
                session = {
                    'messages': [],
                    'messageCount': 0,
                    'role': '',
                    'module': '',
                    'learningMode': 'mixed',
                    'createdAt': datetime.utcnow(),
                }

            messages = session.get('messages', [])

            # Add new message
            messages.append({
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
            })

            # Enforce 30-message cap
            if len(messages) > 30:
                messages = messages[-30:]

            # Update session
            message_count = session.get('messageCount', 0)
            if role == 'user':
                message_count += 1

            self.db.update_document(
                f'users/{uid}/chat_sessions',
                session_id,
                {
                    'messages': messages,
                    'messageCount': message_count,
                    'updatedAt': datetime.utcnow(),
                },
                create_if_missing=True,
            )

        except Exception as e:
            logger.error(f"❌ Failed to store message: {str(e)}")

    def _enforce_rate_limit(self, uid: str, session_id: str) -> Dict:
        """
        Check if user has exceeded the message limit for this session.

        Returns dict with 'allowed' (bool) and 'reason' (str) if blocked.
        """
        try:
            session = self.db.get_document(f'users/{uid}/chat_sessions', session_id)
            if not session:
                return {'allowed': True, 'reason': ''}

            message_count = session.get('messageCount', 0)

            if message_count >= self.max_messages_per_session:
                return {
                    'allowed': False,
                    'reason': (
                        f"You've reached the maximum of {self.max_messages_per_session} "
                        "messages for this session. Please clear the chat to start a "
                        "new conversation. 🔄"
                    ),
                }

            return {'allowed': True, 'reason': ''}

        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {str(e)}")
            # Allow on error to not block the user
            return {'allowed': True, 'reason': ''}
