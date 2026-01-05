"""
Fast roadmap generation using pre-built templates
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime
from app.db.firestore import FirestoreService

logger = logging.getLogger(__name__)

class FastRoadmapGenerator:
    """Fast roadmap generation using templates and smart customization"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        
        # Pre-defined roadmap templates for common roles
        self.role_templates = {
            'frontend-dev': {
                'title': 'Frontend Developer Roadmap',
                'description': 'Complete path to becoming a frontend developer',
                'milestones': [
                    {
                        'title': 'Web Fundamentals',
                        'description': 'Master the core building blocks of web development',
                        'order': 1,
                        'estimatedWeeks': 3,
                        'skills': [
                            {'skillId': 'html', 'skillName': 'HTML', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 20},
                            {'skillId': 'css', 'skillName': 'CSS', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'js', 'skillName': 'JavaScript', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40}
                        ]
                    },
                    {
                        'title': 'Modern JavaScript',
                        'description': 'Advanced JavaScript concepts and ES6+ features',
                        'order': 2,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'js', 'skillName': 'JavaScript', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 30},
                            {'skillId': 'ts', 'skillName': 'TypeScript', 'targetLevel': 'intermediate', 'priority': 'medium', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'React Development',
                        'description': 'Build dynamic user interfaces with React',
                        'order': 3,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'react', 'skillName': 'React', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'redux', 'skillName': 'Redux', 'targetLevel': 'intermediate', 'priority': 'medium', 'estimatedHours': 20}
                        ]
                    },
                    {
                        'title': 'Professional Tools',
                        'description': 'Version control and development workflow',
                        'order': 4,
                        'estimatedWeeks': 2,
                        'skills': [
                            {'skillId': 'git', 'skillName': 'Git', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 15},
                            {'skillId': 'webpack', 'skillName': 'Webpack', 'targetLevel': 'beginner', 'priority': 'low', 'estimatedHours': 10}
                        ]
                    }
                ]
            },
            'backend-dev': {
                'title': 'Backend Developer Roadmap',
                'description': 'Complete path to becoming a backend developer',
                'milestones': [
                    {
                        'title': 'Programming Fundamentals',
                        'description': 'Master core programming concepts',
                        'order': 1,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'python', 'skillName': 'Python', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'sql', 'skillName': 'SQL', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Web Frameworks',
                        'description': 'Build robust web applications',
                        'order': 2,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'flask', 'skillName': 'Flask', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 35},
                            {'skillId': 'django', 'skillName': 'Django', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'Database & APIs',
                        'description': 'Data management and API development',
                        'order': 3,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'postgresql', 'skillName': 'PostgreSQL', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'rest-api', 'skillName': 'REST API', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 20}
                        ]
                    },
                    {
                        'title': 'DevOps Basics',
                        'description': 'Deployment and version control',
                        'order': 4,
                        'estimatedWeeks': 3,
                        'skills': [
                            {'skillId': 'git', 'skillName': 'Git', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 15},
                            {'skillId': 'docker', 'skillName': 'Docker', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 20}
                        ]
                    }
                ]
            },
            'fullstack-dev': {
                'title': 'Full Stack Developer Roadmap',
                'description': 'Complete path to becoming a full stack developer',
                'milestones': [
                    {
                        'title': 'Frontend Basics',
                        'description': 'Essential frontend technologies',
                        'order': 1,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'html', 'skillName': 'HTML', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 20},
                            {'skillId': 'css', 'skillName': 'CSS', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'js', 'skillName': 'JavaScript', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 35}
                        ]
                    },
                    {
                        'title': 'Backend Fundamentals',
                        'description': 'Server-side development basics',
                        'order': 2,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'python', 'skillName': 'Python', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'nodejs', 'skillName': 'Node.js', 'targetLevel': 'intermediate', 'priority': 'medium', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Database & Integration',
                        'description': 'Data management and API integration',
                        'order': 3,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'sql', 'skillName': 'SQL', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'rest-api', 'skillName': 'REST API', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 20}
                        ]
                    },
                    {
                        'title': 'Modern Stack',
                        'description': 'React and modern development tools',
                        'order': 4,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'react', 'skillName': 'React', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'git', 'skillName': 'Git', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 15}
                        ]
                    }
                ]
            },
            'data-scientist': {
                'title': 'Data Scientist Roadmap',
                'description': 'Complete path to becoming a data scientist',
                'milestones': [
                    {
                        'title': 'Programming Foundation',
                        'description': 'Master Python for data science',
                        'order': 1,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'python', 'skillName': 'Python', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 50},
                            {'skillId': 'sql', 'skillName': 'SQL', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Data Analysis',
                        'description': 'Data manipulation and analysis tools',
                        'order': 2,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'pandas', 'skillName': 'Pandas', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 35},
                            {'skillId': 'numpy', 'skillName': 'NumPy', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'Machine Learning',
                        'description': 'ML algorithms and frameworks',
                        'order': 3,
                        'estimatedWeeks': 6,
                        'skills': [
                            {'skillId': 'scikit-learn', 'skillName': 'Scikit-learn', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'tensorflow', 'skillName': 'TensorFlow', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Data Visualization',
                        'description': 'Present insights effectively',
                        'order': 4,
                        'estimatedWeeks': 3,
                        'skills': [
                            {'skillId': 'matplotlib', 'skillName': 'Matplotlib', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 20},
                            {'skillId': 'tableau', 'skillName': 'Tableau', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 15}
                        ]
                    }
                ]
            },
            'devops-engineer': {
                'title': 'DevOps Engineer Roadmap',
                'description': 'Complete path to becoming a DevOps engineer',
                'milestones': [
                    {
                        'title': 'System Administration',
                        'description': 'Linux and system fundamentals',
                        'order': 1,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'linux', 'skillName': 'Linux', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'bash', 'skillName': 'Bash Scripting', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'Containerization',
                        'description': 'Docker and container orchestration',
                        'order': 2,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'docker', 'skillName': 'Docker', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 30},
                            {'skillId': 'kubernetes', 'skillName': 'Kubernetes', 'targetLevel': 'beginner', 'priority': 'high', 'estimatedHours': 35}
                        ]
                    },
                    {
                        'title': 'Cloud Platforms',
                        'description': 'AWS and cloud services',
                        'order': 3,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'aws', 'skillName': 'AWS', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 45},
                            {'skillId': 'terraform', 'skillName': 'Terraform', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'CI/CD & Monitoring',
                        'description': 'Automation and monitoring tools',
                        'order': 4,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'jenkins', 'skillName': 'Jenkins', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'prometheus', 'skillName': 'Prometheus', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 20}
                        ]
                    }
                ]
            },
            'ml-engineer': {
                'title': 'Machine Learning Engineer Roadmap',
                'description': 'Complete path to becoming an ML engineer',
                'milestones': [
                    {
                        'title': 'Programming & Math Foundation',
                        'description': 'Core programming and mathematical concepts',
                        'order': 1,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'python', 'skillName': 'Python', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 50},
                            {'skillId': 'statistics', 'skillName': 'Statistics', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 35}
                        ]
                    },
                    {
                        'title': 'Machine Learning Fundamentals',
                        'description': 'Core ML algorithms and concepts',
                        'order': 2,
                        'estimatedWeeks': 6,
                        'skills': [
                            {'skillId': 'scikit-learn', 'skillName': 'Scikit-learn', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'pandas', 'skillName': 'Pandas', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Deep Learning & Frameworks',
                        'description': 'Neural networks and deep learning',
                        'order': 3,
                        'estimatedWeeks': 7,
                        'skills': [
                            {'skillId': 'tensorflow', 'skillName': 'TensorFlow', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 45},
                            {'skillId': 'pytorch', 'skillName': 'PyTorch', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 35}
                        ]
                    },
                    {
                        'title': 'MLOps & Production',
                        'description': 'Deploy and monitor ML models',
                        'order': 4,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'mlflow', 'skillName': 'MLflow', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'docker', 'skillName': 'Docker', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 20}
                        ]
                    }
                ]
            },
            'cloud-architect': {
                'title': 'Cloud Architect Roadmap',
                'description': 'Complete path to becoming a cloud architect',
                'milestones': [
                    {
                        'title': 'Cloud Fundamentals',
                        'description': 'Core cloud computing concepts',
                        'order': 1,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'aws', 'skillName': 'AWS', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'azure', 'skillName': 'Azure', 'targetLevel': 'beginner', 'priority': 'medium', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Infrastructure as Code',
                        'description': 'Automate infrastructure provisioning',
                        'order': 2,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'terraform', 'skillName': 'Terraform', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 35},
                            {'skillId': 'cloudformation', 'skillName': 'CloudFormation', 'targetLevel': 'intermediate', 'priority': 'medium', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'Security & Compliance',
                        'description': 'Cloud security best practices',
                        'order': 3,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'cloud-security', 'skillName': 'Cloud Security', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 30},
                            {'skillId': 'iam', 'skillName': 'Identity & Access Management', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'Architecture & Design',
                        'description': 'Design scalable cloud solutions',
                        'order': 4,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'microservices', 'skillName': 'Microservices', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 35},
                            {'skillId': 'system-design', 'skillName': 'System Design', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 40}
                        ]
                    }
                ]
            },
            'tech-lead': {
                'title': 'Technical Lead Roadmap',
                'description': 'Complete path to becoming a technical lead',
                'milestones': [
                    {
                        'title': 'Advanced Programming',
                        'description': 'Master programming and architecture',
                        'order': 1,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'system-design', 'skillName': 'System Design', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 45},
                            {'skillId': 'design-patterns', 'skillName': 'Design Patterns', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 35}
                        ]
                    },
                    {
                        'title': 'Leadership & Communication',
                        'description': 'Develop leadership and soft skills',
                        'order': 2,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'team-leadership', 'skillName': 'Team Leadership', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 30},
                            {'skillId': 'communication', 'skillName': 'Technical Communication', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25}
                        ]
                    },
                    {
                        'title': 'Project Management',
                        'description': 'Manage projects and deliverables',
                        'order': 3,
                        'estimatedWeeks': 4,
                        'skills': [
                            {'skillId': 'agile', 'skillName': 'Agile Methodologies', 'targetLevel': 'intermediate', 'priority': 'high', 'estimatedHours': 25},
                            {'skillId': 'project-management', 'skillName': 'Project Management', 'targetLevel': 'intermediate', 'priority': 'medium', 'estimatedHours': 30}
                        ]
                    },
                    {
                        'title': 'Technical Strategy',
                        'description': 'Make architectural and technical decisions',
                        'order': 4,
                        'estimatedWeeks': 5,
                        'skills': [
                            {'skillId': 'architecture', 'skillName': 'Software Architecture', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 40},
                            {'skillId': 'code-review', 'skillName': 'Code Review & Mentoring', 'targetLevel': 'advanced', 'priority': 'high', 'estimatedHours': 25}
                        ]
                    }
                ]
            }
        }
    
    def get_roadmap_template(self, role_id: str) -> Optional[Dict]:
        """Get roadmap template for a specific role"""
        return self.role_templates.get(role_id)
    
    def get_all_templates(self) -> Dict[str, Dict]:
        """Get all available roadmap templates"""
        return self.role_templates
    
    def customize_roadmap(self, template: Dict, user_skills: List[Dict], experience_level: str) -> Dict:
        """
        Customize roadmap template based on user's current skills and experience level
        """
        try:
            # Create a copy of the template
            customized = template.copy()
            
            # Get user's skill IDs and proficiency levels
            user_skill_map = {skill['skillId']: skill.get('proficiency', 'beginner') for skill in user_skills}
            
            # Proficiency level mapping
            level_order = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            
            # Customize each milestone
            for milestone in customized['milestones']:
                customized_skills = []
                
                for skill in milestone['skills']:
                    skill_id = skill['skillId']
                    target_level = skill['targetLevel']
                    
                    # Check if user already has this skill
                    if skill_id in user_skill_map:
                        user_level = user_skill_map[skill_id]
                        user_level_num = level_order.get(user_level, 1)
                        target_level_num = level_order.get(target_level, 2)
                        
                        # Skip if user already exceeds target level
                        if user_level_num >= target_level_num:
                            continue
                        
                        # Reduce estimated hours if user has some knowledge
                        if user_level_num > 1:
                            skill['estimatedHours'] = max(skill['estimatedHours'] * 0.6, 10)
                    
                    # Adjust based on experience level
                    if experience_level == 'advanced':
                        skill['estimatedHours'] = max(skill['estimatedHours'] * 0.8, 10)
                    elif experience_level == 'beginner':
                        skill['estimatedHours'] = skill['estimatedHours'] * 1.2
                    
                    customized_skills.append(skill)
                
                milestone['skills'] = customized_skills
                
                # Recalculate milestone duration
                total_hours = sum(s['estimatedHours'] for s in customized_skills)
                milestone['estimatedWeeks'] = max(1, round(total_hours / 10))  # Assuming 10 hours per week
            
            # Remove empty milestones
            customized['milestones'] = [m for m in customized['milestones'] if m['skills']]
            
            return customized
            
        except Exception as e:
            logger.error(f"Error customizing roadmap: {str(e)}")
            return template
    
    def save_template_to_firestore(self, role_id: str, template: Dict) -> bool:
        """Save roadmap template to Firestore for persistence"""
        try:
            template_data = {
                'roleId': role_id,
                'title': template['title'],
                'description': template.get('description', ''),
                'milestones': template['milestones'],
                'createdAt': datetime.utcnow(),
                'version': '1.0',
                'isActive': True
            }
            
            # Create/update template with role_id as document ID
            return self.db_service.create_document('roadmap_templates', role_id, template_data)
            
        except Exception as e:
            logger.error(f"Error saving template to Firestore: {str(e)}")
            print(f"    Error details: {str(e)}")
            return False
    
    def load_template_from_firestore(self, role_id: str) -> Optional[Dict]:
        """Load roadmap template from Firestore"""
        try:
            templates = self.db_service.query_collection(
                'roadmap_templates',
                [('roleId', '==', role_id), ('isActive', '==', True)]
            )
            
            if templates:
                return templates[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading template from Firestore: {str(e)}")
            return None
    
    def initialize_templates(self) -> bool:
        """Initialize all templates in Firestore"""
        try:
            success_count = 0
            total_templates = len(self.role_templates)
            
            for role_id, template in self.role_templates.items():
                print(f"  Saving template for {role_id}...")
                try:
                    if self.save_template_to_firestore(role_id, template):
                        success_count += 1
                        print(f"  ✅ Saved template for {role_id}")
                    else:
                        print(f"  ❌ Failed to save template for {role_id}")
                except Exception as e:
                    print(f"  ❌ Error saving template for {role_id}: {str(e)}")
            
            print(f"\n📊 Results: {success_count}/{total_templates} templates saved successfully")
            logger.info(f"Initialized {success_count}/{total_templates} templates")
            return success_count == total_templates
            
        except Exception as e:
            logger.error(f"Error initializing templates: {str(e)}")
            print(f"❌ Critical error during initialization: {str(e)}")
            return False