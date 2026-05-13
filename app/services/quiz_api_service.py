import os
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class QuizApiService:
    """Service to interact with QuizAPI.io and normalize question data"""
    
    def __init__(self):
        self.api_key = os.environ.get('QUIZ_API_KEY')
        self.base_url = os.environ.get('QUIZ_API_BASE_URL', 'https://quizapi.io/api/v1/questions')
        
        # Mapping SkillBridge roles to QuizAPI tags/categories
        self.role_mapping = {
            'frontend-dev': {'tags': 'javascript,html,css', 'category': 'Code'},
            'backend-dev': {'tags': 'python,php,sql,nodejs', 'category': 'Code'},
            'devops-engineer': {'tags': 'docker,kubernetes,linux,devops', 'category': 'DevOps'},
            'fullstack-dev': {'tags': 'javascript,nodejs,sql', 'category': 'Code'},
            'data-scientist': {'tags': 'python', 'category': 'Code'},
            'ml-engineer': {'tags': 'python', 'category': 'Code'},
            'cloud-architect': {'tags': 'cloud,devops', 'category': 'DevOps'},
            'tech-lead': {'tags': 'devops,programming', 'category': 'Code'}
        }

    def fetch_questions(self, role_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch questions from QuizAPI and normalize them"""
        if not self.api_key:
            logger.error("QUIZ_API_KEY not found in environment variables")
            return []

        mapping = self.role_mapping.get(role_id, {'tags': 'programming', 'category': 'Code'})
        
        params = {
            'limit': limit,
            'tags': mapping.get('tags'),
            'category': mapping.get('category')
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }

        try:
            logger.info(f"Fetching questions from QuizAPI for role: {role_id}")
            response = requests.get(self.base_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 401:
                logger.error(f"QuizAPI Unauthorized. Response: {response.text}")
                return []
                
            response.raise_for_status()
            
            res_data = response.json()
            
            # Support both {data: [...]} and direct [...] formats
            raw_questions = res_data.get('data', []) if isinstance(res_data, dict) else res_data
            
            if not raw_questions:
                logger.warning(f"No questions returned from QuizAPI for {role_id}")
                return []
                
            return self.normalize_questions(raw_questions, role_id)
            
        except Exception as e:
            logger.error(f"Error fetching questions from QuizAPI: {str(e)}")
            return []

    def normalize_questions(self, raw_questions: List[Dict], role_id: str) -> List[Dict[str, Any]]:
        """Normalize QuizAPI response into SkillBridge internal format"""
        normalized = []
        for q in raw_questions:
            try:
                # Structure detection
                if 'answers' in q and isinstance(q['answers'], list):
                    # NEW STRUCTURE detected in testing
                    # { text: "...", answers: [{text: "...", isCorrect: true}, ...] }
                    options = [a.get('text') for a in q['answers'] if a.get('text')]
                    correct_answer = next((a.get('text') for a in q['answers'] if a.get('isCorrect')), None)
                    question_text = q.get('text')
                else:
                    # OLD/DOCUMENTED STRUCTURE
                    # { question: "...", answers: {answer_a: "...", ...}, correct_answers: {...} }
                    options_dict = q.get('answers', {})
                    options = [val for val in options_dict.values() if val is not None]
                    
                    correct_answers_dict = q.get('correct_answers', {})
                    correct_key = None
                    for key, is_correct in correct_answers_dict.items():
                        if str(is_correct).lower() == 'true':
                            correct_key = key.replace('_correct', '')
                            break
                    
                    correct_answer = options_dict.get(correct_key) if correct_key else None
                    question_text = q.get('question')

                if not correct_answer or len(options) < 2:
                    continue

                normalized.append({
                    'id': f"q_{role_id}_{q.get('id')}",
                    'text': question_text,
                    'options': options,
                    'correctAnswer': correct_answer,
                    'roleId': role_id,
                    'difficulty': str(q.get('difficulty', 'Medium')).lower(),
                    'source': 'quizapi',
                    'category': q.get('category'),
                    'tags': q.get('tags', []) if isinstance(q.get('tags'), list) else []
                })
            except Exception as e:
                logger.warning(f"Failed to normalize question: {str(e)}")
                continue
                
        return normalized
