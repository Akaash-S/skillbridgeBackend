from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import random
from app.db.firestore import FirestoreService
from app.services.quiz_api_service import QuizApiService

logger = logging.getLogger(__name__)

class AssessmentService:
    """Service for managing proctored assessments and results using a hybrid QuizAPI architecture"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        self.quiz_api = QuizApiService()
        self.collection = 'assessment_sessions'
        self.questions_collection = 'role_assessments'

    def get_questions(self, role_id: str, limit: int = 10) -> List[Dict]:
        """Fetch randomized questions with hybrid caching logic"""
        try:
            # 1. Try to get from Firestore cache
            filters = [('roleId', '==', role_id)]
            questions = self.db_service.query_collection(self.questions_collection, filters)
            
            # 2. If insufficient questions in cache, fetch from QuizAPI
            if len(questions) < limit:
                logger.info(f"Insufficient questions for {role_id} in cache ({len(questions)}/{limit}). Fetching from QuizAPI...")
                new_questions = self.quiz_api.fetch_questions(role_id, limit=20)
                
                if new_questions:
                    # Store new questions in Firestore cache
                    for q in new_questions:
                        # Check if question already exists in our cache list to avoid duplicates
                        if not any(existing.get('id') == q['id'] for existing in questions):
                            self.db_service.create_document(self.questions_collection, q['id'], q)
                            questions.append(q)
            
            # 3. Fallback to static defaults if still empty
            if not questions:
                logger.warning(f"No questions found for role {role_id}, falling back to defaults")
                return self._get_fallback_questions(role_id)[:limit]
            
            # 4. Randomize and limit
            random.shuffle(questions)
            return questions[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching questions: {str(e)}")
            return self._get_fallback_questions(role_id)[:limit]

    def start_session(self, uid: str, role_id: str) -> Optional[str]:
        """Initialize a new assessment session"""
        try:
            session_id = f"sess_{uid}_{int(datetime.utcnow().timestamp())}"
            session_data = {
                'sessionId': session_id,
                'uid': uid,
                'roleId': role_id,
                'status': 'active',
                'startTime': datetime.utcnow(),
                'violations': 0,
                'violationLogs': [],
                'score': 0,
                'completed': False,
                'terminated': False
            }
            
            if self.db_service.create_document(self.collection, session_id, session_data):
                return session_id
            return None
        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            return None

    def log_violation(self, session_id: str, violation_type: str, details: str = "") -> Dict:
        """Log a violation and check for termination"""
        try:
            session = self.db_service.get_document(self.collection, session_id)
            if not session:
                return {'error': 'Session not found'}
            
            violations = session.get('violations', 0) + 1
            violation_logs = session.get('violationLogs', [])
            violation_logs.append({
                'type': violation_type,
                'details': details,
                'timestamp': datetime.utcnow()
            })
            
            terminated = violations >= 3
            update_data = {
                'violations': violations,
                'violationLogs': violation_logs,
                'terminated': terminated,
                'status': 'terminated' if terminated else 'active'
            }
            
            self.db_service.update_document(self.collection, session_id, update_data)
            
            # Create EXAM_VIOLATION in activity_logs for proctoring center visibility
            uid = session.get('uid')
            role_id = session.get('roleId', 'unknown-assessment')
            
            # Map roleId to assessmentName
            role_names = {
                'frontend-dev': 'Frontend React Core Evaluation',
                'backend-dev': 'Backend API Core Architecture',
                'fullstack-dev': 'Fullstack Engineering Assessment',
                'data-scientist': 'Data Science & Machine Learning',
                'devops-engineer': 'DevOps & Kubernetes Infrastructure Orchestration',
                'cloud-architect': 'Cloud Architecture Design'
            }
            assessment_name = role_names.get(role_id, role_id.replace('-', ' ').title())
            
            user_doc = self.db_service.get_document('users', uid) if uid else None
            user_name = user_doc.get('name', 'Learner') if user_doc else 'Learner'
            user_email = user_doc.get('email', 'learner@example.com') if user_doc else 'learner@example.com'
            
            violation_doc = {
                'uid': uid,
                'userName': user_name,
                'userEmail': user_email,
                'assessmentName': assessment_name,
                'message': details or f"Violation detected on frontend: {violation_type}",
                'createdAt': datetime.utcnow(),
                'status': 'pending',
                'severity': 'high' if 'exit' in violation_type.lower() or terminated else 'medium',
                'type': 'EXAM_VIOLATION'
            }
            
            import uuid
            violation_id = f"viol_{uuid.uuid4().hex}"
            self.db_service.create_document('activity_logs', violation_id, violation_doc)
            
            return {
                'violations': violations,
                'terminated': terminated,
                'maxViolations': 3
            }
        except Exception as e:
            logger.error(f"Error logging violation: {str(e)}")
            return {'error': str(e)}

    def submit_assessment(self, session_id: str, answers: Dict[str, str]) -> Dict:
        """Calculate score and finalize session with strict server-side validation"""
        try:
            session = self.db_service.get_document(self.collection, session_id)
            if not session:
                return {'error': 'Session not found'}
            
            if session.get('completed') or session.get('terminated'):
                return {'error': 'Session already finalized'}
            
            role_id = session.get('roleId')
            # Fetch all questions for this role to verify answers
            filters = [('roleId', '==', role_id)]
            questions = self.db_service.query_collection(self.questions_collection, filters)
            
            # Add fallback questions to search if Firestore was empty
            if not questions:
                questions = self._get_fallback_questions(role_id)
            
            correct_count = 0
            total_questions = len(answers)
            
            if total_questions == 0:
                return {'error': 'No answers submitted'}
            
            for q_id, user_answer in answers.items():
                # Find question in our fetched list
                question = next((q for q in questions if q.get('id') == q_id), None)
                if question:
                    # Case insensitive comparison for robustness
                    if str(question.get('correctAnswer')).strip().lower() == str(user_answer).strip().lower():
                        correct_count += 1
                else:
                    logger.warning(f"Submitted answer for unknown question ID: {q_id}")
            
            score = (correct_count / total_questions * 100)
            passed = score >= 70 # 70% passing grade
            
            # Final security check: violations
            if session.get('violations', 0) >= 3:
                passed = False
                status = 'terminated'
            else:
                status = 'passed' if passed else 'failed'
            
            update_data = {
                'score': round(score, 2),
                'completed': True,
                'endTime': datetime.utcnow(),
                'status': status,
                'passed': passed
            }
            
            self.db_service.update_document(self.collection, session_id, update_data)
            
            # Update user state/certificate eligibility
            if passed:
                self._unlock_certificate(session.get('uid'), role_id)
            
            return {
                'score': round(score, 2),
                'passed': passed,
                'violations': session.get('violations', 0)
            }
        except Exception as e:
            logger.error(f"Error submitting assessment: {str(e)}")
            return {'error': str(e)}

    def check_eligibility(self, uid: str, role_id: str) -> Dict:
        """Check if user can take the assessment"""
        try:
            # 1. Check for recent passed assessment
            filters = [
                ('uid', '==', uid),
                ('roleId', '==', role_id),
                ('status', '==', 'passed')
            ]
            results = self.db_service.query_collection(self.collection, filters)
            
            if results:
                return {'eligible': False, 'reason': 'Assessment already passed'}
            
            return {'eligible': True}
        except Exception as e:
            logger.error(f"Error checking eligibility: {str(e)}")
            return {'eligible': False, 'error': str(e)}

    def get_user_sessions(self, uid: str) -> List[Dict]:
        """Fetch all assessment sessions for a user"""
        try:
            return self.db_service.query_collection(self.collection, [('uid', '==', uid)])
        except Exception as e:
            logger.error(f"Error getting sessions for user {uid}: {str(e)}")
            return []


    def seed_from_quizapi(self, role_id: str = None) -> Dict:
        """Manually trigger seeding from QuizAPI for one or all roles"""
        roles = [role_id] if role_id else ['frontend-dev', 'backend-dev', 'fullstack-dev', 'data-scientist', 'devops-engineer', 'cloud-architect']
        results = {}
        
        for r in roles:
            try:
                new_questions = self.quiz_api.fetch_questions(r, limit=50)
                count = 0
                for q in new_questions:
                    if self.db_service.create_document(self.questions_collection, q['id'], q):
                        count += 1
                results[r] = f"Seeded {count} questions"
            except Exception as e:
                results[r] = f"Error: {str(e)}"
        
        return results

    def _unlock_certificate(self, uid: str, role_id: str):
        """Mark user as eligible for certificate in Firestore"""
        try:
            user_state_id = f"state_{uid}"
            state = self.db_service.get_document('user_states', user_state_id)
            
            if state:
                eligible_roles = state.get('eligibleCertificates', [])
                if role_id not in eligible_roles:
                    eligible_roles.append(role_id)
                    self.db_service.update_document('user_states', user_state_id, {
                        'eligibleCertificates': eligible_roles
                    })
            else:
                # Create state if it doesn't exist
                self.db_service.create_document('user_states', user_state_id, {
                    'uid': uid,
                    'eligibleCertificates': [role_id],
                    'updatedAt': datetime.utcnow()
                })
        except Exception as e:
            logger.error(f"Error unlocking certificate: {str(e)}")

    def _get_fallback_questions(self, role_id: str) -> List[Dict]:
        """Static fallback questions for various roles"""
        questions = {
            'frontend-dev': [
                {
                    'id': 'fe_1',
                    'text': 'What is the purpose of React\'s useEffect hook?',
                    'options': [
                        'To perform side effects in functional components',
                        'To manage state in class components',
                        'To styles elements directly',
                        'To handle routing'
                    ],
                    'correctAnswer': 'To perform side effects in functional components'
                },
                {
                    'id': 'fe_2',
                    'text': 'Which CSS property is used to create a flex container?',
                    'options': ['display: block', 'display: flex', 'display: grid', 'float: left'],
                    'correctAnswer': 'display: flex'
                },
                {
                    'id': 'fe_3',
                    'text': 'What does DOM stand for?',
                    'options': [
                        'Data Object Model',
                        'Document Object Model',
                        'Dynamic Object Management',
                        'Display Order Method'
                    ],
                    'correctAnswer': 'Document Object Model'
                }
            ],
            'backend-dev': [
                {
                    'id': 'be_1',
                    'text': 'What is the main difference between SQL and NoSQL databases?',
                    'options': [
                        'SQL is relational, NoSQL is non-relational',
                        'SQL is faster for all operations',
                        'NoSQL only stores JSON',
                        'SQL cannot handle large data'
                    ],
                    'correctAnswer': 'SQL is relational, NoSQL is non-relational'
                },
                {
                    'id': 'be_2',
                    'text': 'What does a 404 HTTP status code mean?',
                    'options': ['Success', 'Forbidden', 'Not Found', 'Internal Server Error'],
                    'correctAnswer': 'Not Found'
                }
            ]
        }
        
        # Default to common tech questions if role not found
        role_questions = questions.get(role_id, [
            {
                'id': 'gen_1',
                'text': 'What is Git?',
                'options': ['A programming language', 'A version control system', 'A cloud provider', 'A database'],
                'correctAnswer': 'A version control system'
            },
            {
                'id': 'gen_2',
                'text': 'What does API stand for?',
                'options': [
                    'Application Programming Interface',
                    'Advanced Program Integration',
                    'Automated Protocol Index',
                    'Access Point Information'
                ],
                'correctAnswer': 'Application Programming Interface'
            }
        ])
        
        for q in role_questions:
            q['roleId'] = role_id
            
        return role_questions
