import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.db.firestore import FirestoreService

logger = logging.getLogger(__name__)

# Rich catalog of multiple choice questions per skill
MASTER_QUIZ_CATALOG = {
    'html': [
        {'id': 'html_1', 'question': 'What does HTML stand for?', 'options': ['Hyper Text Markup Language', 'High Tech Markup Language', 'Hyper Link Markup Language', 'Home Tool Markup Language'], 'correctAnswer': 0},
        {'id': 'html_2', 'question': 'Which HTML element is used for the largest heading?', 'options': ['<heading>', '<h6>', '<h1>', '<head>'], 'correctAnswer': 2},
        {'id': 'html_3', 'question': 'What is the correct HTML element for inserting a line break?', 'options': ['<break>', '<lb>', '<br>', '<hr>'], 'correctAnswer': 2},
        {'id': 'html_4', 'question': 'Which character is used to indicate an end tag in HTML?', 'options': ['^', '/', '*', '<'], 'correctAnswer': 1},
        {'id': 'html_5', 'question': 'Which attribute is used to specify a unique identifier for an HTML element?', 'options': ['class', 'id', 'name', 'style'], 'correctAnswer': 1}
    ],
    'css': [
        {'id': 'css_1', 'question': 'What does CSS stand for?', 'options': ['Computer Style Sheets', 'Creative Style Sheets', 'Cascading Style Sheets', 'Colorful Style Sheets'], 'correctAnswer': 2},
        {'id': 'css_2', 'question': 'Where in an HTML document is the correct place to refer to an external style sheet?', 'options': ['At the end of the document', 'In the <body> section', 'In the <head> section', 'In the <title> section'], 'correctAnswer': 2},
        {'id': 'css_3', 'question': 'Which HTML tag is used to define an internal style sheet?', 'options': ['<css>', '<script>', '<style>', '<link>'], 'correctAnswer': 2},
        {'id': 'css_4', 'question': 'Which CSS property is used to change the text color of an element?', 'options': ['text-color', 'color', 'fgcolor', 'font-color'], 'correctAnswer': 1},
        {'id': 'css_5', 'question': 'Which CSS property controls the text size?', 'options': ['text-size', 'font-style', 'font-size', 'text-style'], 'correctAnswer': 2}
    ],
    'javascript': [
        {'id': 'js_1', 'question': 'Which of the following is NOT a valid JavaScript data type?', 'options': ['Undefined', 'Boolean', 'Float', 'Symbol'], 'correctAnswer': 2},
        {'id': 'js_2', 'question': 'What is the correct way to write comments in JavaScript?', 'options': ['<!-- comment -->', '// comment', '/* comment */', 'Both // comment and /* comment */'], 'correctAnswer': 3},
        {'id': 'js_3', 'question': 'Which method is used to add an element to the end of an array in JavaScript?', 'options': ['push()', 'pop()', 'shift()', 'unshift()'], 'correctAnswer': 0},
        {'id': 'js_4', 'question': 'What is the purpose of the "use strict" directive in JavaScript?', 'options': ['To enable strict type checking', 'To enforce stricter parsing and error handling at runtime', 'To disable dynamic execution', 'To enable ES6 features'], 'correctAnswer': 1},
        {'id': 'js_5', 'question': 'What does "NaN" stand for in JavaScript?', 'options': ['Not a Number', 'Null and Void', 'Negative and Null', 'Number Array Null'], 'correctAnswer': 0}
    ],
    'typescript': [
        {'id': 'ts_1', 'question': 'Which keyword is used in TypeScript to declare an interface?', 'options': ['interface', 'type', 'class', 'struct'], 'correctAnswer': 0},
        {'id': 'ts_2', 'question': 'How do you define an optional property in a TypeScript interface?', 'options': ['Using a ? suffix after the property name', 'Using the optional keyword', 'Setting the property type to null', 'Using a * prefix'], 'correctAnswer': 0},
        {'id': 'ts_3', 'question': 'What is the type of any variable in TypeScript if it is not explicitly declared and type inference cannot determine it?', 'options': ['unknown', 'void', 'any', 'never'], 'correctAnswer': 2},
        {'id': 'ts_4', 'question': 'Which of the following compiles TypeScript files into JavaScript?', 'options': ['tsc', 'typescript-compiler', 'node-ts', 'tjs'], 'correctAnswer': 0},
        {'id': 'ts_5', 'question': 'What is the utility type in TypeScript that makes all properties of an object optional?', 'options': ['Optional<T>', 'Partial<T>', 'Pick<T>', 'Omit<T>'], 'correctAnswer': 1}
    ],
    'react': [
        {'id': 'react_1', 'question': 'What is the correct way to define state in a functional React component?', 'options': ['this.state = {}', 'const [state, setState] = useState(initialState)', 'const state = React.state()', 'let state = {}'], 'correctAnswer': 1},
        {'id': 'react_2', 'question': 'Which hook is used to perform side effects in functional React components?', 'options': ['useAction', 'useContext', 'useEffect', 'useReducer'], 'correctAnswer': 2},
        {'id': 'react_3', 'question': 'What are props in React?', 'options': ['Internal component state', 'A method to force re-render', 'External inputs passed into a component', 'A state management library'], 'correctAnswer': 2},
        {'id': 'react_4', 'question': 'What is the purpose of "key" prop in React lists?', 'options': ['To secure list items', 'To identify which items have changed, been added, or removed', 'To apply CSS styles', 'To bind click handlers'], 'correctAnswer': 1},
        {'id': 'react_5', 'question': 'What is React JSX?', 'options': ['A build tool for React', 'A styling framework', 'A syntax extension to JavaScript that describes UI', 'A local database'], 'correctAnswer': 2}
    ],
    'python': [
        {'id': 'py_1', 'question': 'Which of the following is the correct file extension for Python files?', 'options': ['.py', '.pyt', '.pt', '.python'], 'correctAnswer': 0},
        {'id': 'py_2', 'question': 'How do you create a variable with the numeric value 5 in Python?', 'options': ['num = 5', 'int num = 5', 'num := 5', 'var num = 5'], 'correctAnswer': 0},
        {'id': 'py_3', 'question': 'Which keyword is used to define a function in Python?', 'options': ['func', 'def', 'function', 'define'], 'correctAnswer': 1},
        {'id': 'py_4', 'question': 'Which collection is ordered, changeable, and allows duplicate members in Python?', 'options': ['List', 'Tuple', 'Set', 'Dictionary'], 'correctAnswer': 0},
        {'id': 'py_5', 'question': 'What is the output of len([1, 2, 3]) in Python?', 'options': ['1', '2', '3', 'Error'], 'correctAnswer': 2}
    ],
    'sql': [
        {'id': 'sql_1', 'question': 'Which SQL statement is used to extract data from a database?', 'options': ['SELECT', 'EXTRACT', 'GET', 'OPEN'], 'correctAnswer': 0},
        {'id': 'sql_2', 'question': 'Which SQL statement is used to update data in a database?', 'options': ['SAVE', 'MODIFY', 'UPDATE', 'WRITE'], 'correctAnswer': 2},
        {'id': 'sql_3', 'question': 'Which SQL clause is used to filter records?', 'options': ['IF', 'WHERE', 'HAVING', 'GROUP BY'], 'correctAnswer': 1},
        {'id': 'sql_4', 'question': 'What does SQL stand for?', 'options': ['Strong Query Language', 'Structured Query Language', 'Simple Query Language', 'Standard Query Language'], 'correctAnswer': 1},
        {'id': 'sql_5', 'question': 'How do you select all columns from a table named "Customers"?', 'options': ['SELECT ALL Customers', 'SELECT * FROM Customers', 'SELECT Customers', 'GET * FROM Customers'], 'correctAnswer': 1}
    ],
    'docker': [
        {'id': 'docker_1', 'question': 'What is a Docker image?', 'options': ['A running instance of a container', 'A read-only template with instructions for creating a Docker container', 'A physical server hosting containers', 'A graphical user interface for Docker'], 'correctAnswer': 1},
        {'id': 'docker_2', 'question': 'Which Docker command is used to run a container from an image?', 'options': ['docker execute', 'docker build', 'docker run', 'docker start'], 'correctAnswer': 2},
        {'id': 'docker_3', 'question': 'What is the purpose of a Dockerfile?', 'options': ['To configure network ports', 'A text document that contains all the commands a user could call on the command line to assemble an image', 'To list running containers', 'To manage Docker volumes'], 'correctAnswer': 1},
        {'id': 'docker_4', 'question': 'Which Docker command is used to list all active containers?', 'options': ['docker containers', 'docker ps', 'docker ls', 'docker show'], 'correctAnswer': 1},
        {'id': 'docker_5', 'question': 'What is Docker Compose used for?', 'options': ['Building single containers', 'Defining and running multi-container Docker applications', 'Monitoring host CPU usage', 'Compiling JavaScript applications'], 'correctAnswer': 1}
    ],
    'kubernetes': [
        {'id': 'k8s_1', 'question': 'What is the smallest deployable unit in Kubernetes?', 'options': ['Container', 'Pod', 'Service', 'Deployment'], 'correctAnswer': 1},
        {'id': 'k8s_2', 'question': 'Which command line tool is used to interact with Kubernetes clusters?', 'options': ['kubecontrol', 'k8s-cli', 'kubectl', 'kubeadm'], 'correctAnswer': 2},
        {'id': 'k8s_3', 'question': 'What is the main role of a Kubernetes Service?', 'options': ['To define container storage', 'To expose an application running on a set of Pods as a network service', 'To schedule cron jobs', 'To monitor node CPU temperature'], 'correctAnswer': 1},
        {'id': 'k8s_4', 'question': 'What does the replica count in a Kubernetes Deployment specify?', 'options': ['The number of clusters in a cluster group', 'The number of identical Pods that should run at any given time', 'The number of container ports exposed', 'The number of deployment backups'], 'correctAnswer': 1},
        {'id': 'k8s_5', 'question': 'Which Kubernetes component schedules Pods onto appropriate Nodes?', 'options': ['kube-apiserver', 'kube-scheduler', 'etcd', 'kube-controller-manager'], 'correctAnswer': 1}
    ],
    'aws': [
        {'id': 'aws_1', 'question': 'What is AWS EC2?', 'options': ['Simple Storage Service', 'Virtual servers in the cloud', 'A serverless database service', 'A content delivery network'], 'correctAnswer': 1},
        {'id': 'aws_2', 'question': 'Which AWS service is designed for object storage?', 'options': ['EC2', 'S3', 'RDS', 'Lambda'], 'correctAnswer': 1},
        {'id': 'aws_3', 'question': 'What is AWS IAM used for?', 'options': ['Database management', 'Managing access and permissions to AWS resources securely', 'Caching web content', 'Routing domain traffic'], 'correctAnswer': 1},
        {'id': 'aws_4', 'question': 'Which AWS service lets you run code without provisioning or managing servers?', 'options': ['Elastic Beanstalk', 'EC2', 'Lambda', 'ECS'], 'correctAnswer': 2},
        {'id': 'aws_5', 'question': 'What is AWS RDS?', 'options': ['A managed Relational Database Service', 'Redundant Domain Server', 'Route Delivery System', 'Remote Data Storage'], 'correctAnswer': 0}
    ],
    'git': [
        {'id': 'git_1', 'question': 'Which Git command is used to record file changes in the local repository history?', 'options': ['git add', 'git save', 'git commit', 'git push'], 'correctAnswer': 2},
        {'id': 'git_2', 'question': 'Which Git command is used to download content from a remote repository and update the local repository?', 'options': ['git pull', 'git download', 'git clone', 'git checkout'], 'correctAnswer': 0},
        {'id': 'git_3', 'question': 'What is the staging area in Git?', 'options': ['A remote repository backup', 'A draft file containing comments', 'A file that stores all commits', 'A workspace area where changes are prepared before committing'], 'correctAnswer': 3},
        {'id': 'git_4', 'question': 'How do you create a new Git branch named "feature-login"?', 'options': ['git branch create feature-login', 'git checkout -b feature-login', 'git newfeature feature-login', 'git add branch feature-login'], 'correctAnswer': 1},
        {'id': 'git_5', 'question': 'What is the purpose of Git merge?', 'options': ['To copy repositories', 'To combine histories from different branches', 'To delete empty folders', 'To stage file modifications'], 'correctAnswer': 1}
    ]
}

# General backup questions to satisfy the 5 MCQ requirement
GENERAL_QUIZ_POOL = [
    {'id': 'gen_1', 'question': 'Which of the following is a key tenet of Clean Code?', 'options': ['Write comments for every line of code', 'Keep functions small and focused on a single task', 'Use extremely long variables names', 'Avoid writing modular tests'], 'correctAnswer': 1},
    {'id': 'gen_2', 'question': 'What is the purpose of unit testing in software development?', 'options': ['To verify that individual components of the software work as expected', 'To style the application visual interface', 'To speed up server responses', 'To deploy applications automatically'], 'correctAnswer': 0},
    {'id': 'gen_3', 'question': 'What does the term DRY stand for in programming?', 'options': ['Do React Yourself', 'Don\'t Repeat Yourself', 'Database Routing Yield', 'Data Retrieval Yield'], 'correctAnswer': 1},
    {'id': 'gen_4', 'question': 'Which data structure follows a First-In-First-Out (FIFO) principle?', 'options': ['Stack', 'Queue', 'Array', 'Binary Tree'], 'correctAnswer': 1},
    {'id': 'gen_5', 'question': 'Which of the following is a common protocol used for web communications?', 'options': ['FTP', 'SMTP', 'HTTP', 'SSH'], 'correctAnswer': 2}
]

class QuizService:
    """Service to generate module quizzes and evaluate/grade submissions"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        
    def generate_quiz(self, skills: List[Dict[str, Any]], module_index: int) -> List[Dict[str, Any]]:
        """Generate 5 MCQs based on the skills in the module"""
        pool = []
        
        # Pull questions for skills in this module
        for skill in skills:
            skill_id = skill.get('skillId', '').lower()
            # Try exact match or base prefix match (e.g. js -> javascript)
            matched_key = None
            if skill_id in MASTER_QUIZ_CATALOG:
                matched_key = skill_id
            elif skill_id == 'js' and 'javascript' in MASTER_QUIZ_CATALOG:
                matched_key = 'javascript'
            elif skill_id == 'ts' and 'typescript' in MASTER_QUIZ_CATALOG:
                matched_key = 'typescript'
            elif skill_id == 'k8s' and 'kubernetes' in MASTER_QUIZ_CATALOG:
                matched_key = 'kubernetes'
                
            if matched_key:
                pool.extend(MASTER_QUIZ_CATALOG[matched_key])
                
        # If pool has less than 5 questions, supplement with generic questions
        if len(pool) < 5:
            # Generate generic questions matching the skill names
            for skill in skills:
                name = skill.get('skillName', skill.get('skillId', 'Technology'))
                skill_id = skill.get('skillId', 'gen')
                pool.append({
                    'id': f'dyn_{skill_id}_1',
                    'question': f'What is the primary purpose of {name} in software development?',
                    'options': [
                        f'To design graphic user interface mockups',
                        f'To solve technical challenges related to {name}',
                        f'To manage team building events',
                        f'To compile source code into operating systems'
                    ],
                    'correctAnswer': 1
                })
                pool.append({
                    'id': f'dyn_{skill_id}_2',
                    'question': f'Which of the following is a common best practice when working with {name}?',
                    'options': [
                        f'Avoid updating dependencies',
                        f'Write clean, modular, and readable structures',
                        f'Store passwords in plaintext comments',
                        f'Run deployments without testing changes'
                    ],
                    'correctAnswer': 1
                })
                
            # Add general software engineering questions if we are still short
            pool.extend(GENERAL_QUIZ_POOL)
            
        # Select 5 unique questions from the pool. Use deterministic random based on module_index to ensure 
        # consistency within a session, but shuffle a bit.
        rng = random.Random(module_index + 42)
        selected_questions = rng.sample(pool, 5)
        
        # Remove correct answers before returning to client for security
        client_questions = []
        for q in selected_questions:
            client_questions.append({
                'id': q['id'],
                'question': q['question'],
                'options': q['options']
            })
            
        return client_questions
        
    def grade_quiz(self, uid: str, module_index: int, answers: Dict[str, int]) -> Dict[str, Any]:
        """
        Grade a quiz submission
        answers is a dictionary of { question_id: selected_option_index }
        """
        try:
            score = 0
            total = len(answers) if answers else 5
            if total != 5:
                # Force total to 5
                total = 5
                
            # Grade each submitted question
            for q_id, selected_idx in answers.items():
                correct_idx = self._get_correct_answer(q_id)
                if correct_idx is not None and selected_idx == correct_idx:
                    score += 1
                    
            passed = score >= 4  # 4/5 is 80%, which is >= 70% passing threshold
            
            # Save the quiz attempt in firestore
            attempt_data = {
                'uid': uid,
                'moduleIndex': module_index,
                'score': score,
                'passed': passed,
                'answers': answers,
                'timestamp': datetime.utcnow()
            }
            
            attempt_id = f"{uid}_{module_index}_{int(datetime.utcnow().timestamp())}"
            self.db_service.create_document('quiz_attempts', attempt_id, attempt_data)
            
            # Count historical attempts for this specific module
            historical_attempts = self.db_service.query_collection('quiz_attempts', [
                ('uid', '==', uid),
                ('moduleIndex', '==', module_index)
            ])
            attempts_count = len(historical_attempts)
            
            return {
                'score': score,
                'passed': passed,
                'quizAttempts': attempts_count
            }
            
        except Exception as e:
            logger.error(f"Error grading quiz for user {uid}, module {module_index}: {str(e)}")
            return {
                'score': 0,
                'passed': False,
                'quizAttempts': 1
            }
            
    def _get_correct_answer(self, question_id: str) -> Optional[int]:
        """Look up correct answer index from catalogs"""
        # Search in master catalog
        for skill, questions in MASTER_QUIZ_CATALOG.items():
            for q in questions:
                if q['id'] == question_id:
                    return q['correctAnswer']
                    
        # Search in general pool
        for q in GENERAL_QUIZ_POOL:
            if q['id'] == question_id:
                return q['correctAnswer']
                
        # Check dynamic generated questions
        if question_id.startswith('dyn_'):
            return 1 # All dynamic questions generated above use index 1 as correct answer
            
        return None
