#!/usr/bin/env python3
"""
SkillBridge Suite - Database Seeding Script
Seeds Firestore with initial master data for skills, roadmap templates, and learning resources.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.firestore import FirestoreService

# Load environment variables
load_dotenv()

def seed_skills_master():
    """Seed the skills_master collection with comprehensive skill data"""
    
    skills_data = [
        # Programming Languages
        {
            "skillId": "javascript",
            "name": "JavaScript",
            "category": "Programming Languages",
            "type": "technical",
            "aliases": ["js", "ecmascript"],
            "prerequisites": [],
            "relatedSkills": ["typescript", "nodejs", "react"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "typescript",
            "name": "TypeScript",
            "category": "Programming Languages",
            "type": "technical",
            "aliases": ["ts"],
            "prerequisites": ["javascript"],
            "relatedSkills": ["javascript", "react", "angular"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "python",
            "name": "Python",
            "category": "Programming Languages",
            "type": "technical",
            "aliases": ["py"],
            "prerequisites": [],
            "relatedSkills": ["django", "flask", "pandas", "tensorflow"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "java",
            "name": "Java",
            "category": "Programming Languages",
            "type": "technical",
            "aliases": [],
            "prerequisites": [],
            "relatedSkills": ["spring", "springboot", "android"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        
        # Frontend Technologies
        {
            "skillId": "react",
            "name": "React",
            "category": "Frontend",
            "type": "technical",
            "aliases": ["reactjs", "react.js"],
            "prerequisites": ["javascript", "html", "css"],
            "relatedSkills": ["redux", "nextjs", "typescript"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "vue",
            "name": "Vue.js",
            "category": "Frontend",
            "type": "technical",
            "aliases": ["vuejs", "vue.js"],
            "prerequisites": ["javascript", "html", "css"],
            "relatedSkills": ["nuxt", "vuex"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "angular",
            "name": "Angular",
            "category": "Frontend",
            "type": "technical",
            "aliases": ["angularjs"],
            "prerequisites": ["typescript", "html", "css"],
            "relatedSkills": ["rxjs", "ngrx"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "html",
            "name": "HTML5",
            "category": "Frontend",
            "type": "technical",
            "aliases": ["html5", "markup"],
            "prerequisites": [],
            "relatedSkills": ["css", "javascript"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "css",
            "name": "CSS3",
            "category": "Frontend",
            "type": "technical",
            "aliases": ["css3", "styling"],
            "prerequisites": ["html"],
            "relatedSkills": ["sass", "tailwind", "bootstrap"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        
        # Backend Technologies
        {
            "skillId": "nodejs",
            "name": "Node.js",
            "category": "Backend",
            "type": "technical",
            "aliases": ["node", "node.js"],
            "prerequisites": ["javascript"],
            "relatedSkills": ["express", "npm", "mongodb"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "express",
            "name": "Express.js",
            "category": "Backend",
            "type": "technical",
            "aliases": ["expressjs", "express.js"],
            "prerequisites": ["nodejs"],
            "relatedSkills": ["nodejs", "mongodb", "rest"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "django",
            "name": "Django",
            "category": "Backend",
            "type": "technical",
            "aliases": [],
            "prerequisites": ["python"],
            "relatedSkills": ["python", "postgresql", "rest"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "flask",
            "name": "Flask",
            "category": "Backend",
            "type": "technical",
            "aliases": [],
            "prerequisites": ["python"],
            "relatedSkills": ["python", "sqlalchemy", "rest"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        
        # Database Technologies
        {
            "skillId": "postgresql",
            "name": "PostgreSQL",
            "category": "Database",
            "type": "technical",
            "aliases": ["postgres", "psql"],
            "prerequisites": ["sql"],
            "relatedSkills": ["sql", "database-design"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "mongodb",
            "name": "MongoDB",
            "category": "Database",
            "type": "technical",
            "aliases": ["mongo"],
            "prerequisites": [],
            "relatedSkills": ["nosql", "mongoose"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "sql",
            "name": "SQL",
            "category": "Database",
            "type": "technical",
            "aliases": ["structured-query-language"],
            "prerequisites": [],
            "relatedSkills": ["postgresql", "mysql", "database-design"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        
        # DevOps & Cloud
        {
            "skillId": "docker",
            "name": "Docker",
            "category": "DevOps & Cloud",
            "type": "technical",
            "aliases": ["containerization"],
            "prerequisites": [],
            "relatedSkills": ["kubernetes", "docker-compose"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "kubernetes",
            "name": "Kubernetes",
            "category": "DevOps & Cloud",
            "type": "technical",
            "aliases": ["k8s"],
            "prerequisites": ["docker"],
            "relatedSkills": ["docker", "helm", "devops"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "aws",
            "name": "Amazon Web Services",
            "category": "DevOps & Cloud",
            "type": "technical",
            "aliases": ["amazon-web-services"],
            "prerequisites": [],
            "relatedSkills": ["cloud-computing", "ec2", "s3"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        
        # Data Science & ML
        {
            "skillId": "machine-learning",
            "name": "Machine Learning",
            "category": "Data Science",
            "type": "technical",
            "aliases": ["ml", "artificial-intelligence"],
            "prerequisites": ["python", "statistics"],
            "relatedSkills": ["tensorflow", "pytorch", "pandas"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "tensorflow",
            "name": "TensorFlow",
            "category": "Data Science",
            "type": "technical",
            "aliases": ["tf"],
            "prerequisites": ["python", "machine-learning"],
            "relatedSkills": ["keras", "deep-learning"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "pandas",
            "name": "Pandas",
            "category": "Data Science",
            "type": "technical",
            "aliases": [],
            "prerequisites": ["python"],
            "relatedSkills": ["numpy", "data-analysis"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        
        # Soft Skills
        {
            "skillId": "communication",
            "name": "Communication",
            "category": "Soft Skills",
            "type": "soft",
            "aliases": ["verbal-communication", "written-communication"],
            "prerequisites": [],
            "relatedSkills": ["leadership", "teamwork"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "leadership",
            "name": "Leadership",
            "category": "Soft Skills",
            "type": "soft",
            "aliases": ["team-leadership", "management"],
            "prerequisites": ["communication"],
            "relatedSkills": ["communication", "project-management"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "skillId": "problem-solving",
            "name": "Problem Solving",
            "category": "Soft Skills",
            "type": "soft",
            "aliases": ["analytical-thinking", "critical-thinking"],
            "prerequisites": [],
            "relatedSkills": ["algorithms", "debugging"],
            "levels": ["beginner", "intermediate", "advanced"],
            "source": "manual",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
    ]
    
    return skills_data

def seed_roadmap_templates():
    """Seed roadmap templates for common career paths"""
    
    templates_data = [
        {
            "roleId": "frontend-developer",
            "title": "Frontend Developer",
            "description": "Complete roadmap to become a proficient frontend developer",
            "skills": [
                {"skillId": "html", "order": 1, "minLevel": "intermediate"},
                {"skillId": "css", "order": 2, "minLevel": "intermediate"},
                {"skillId": "javascript", "order": 3, "minLevel": "advanced"},
                {"skillId": "react", "order": 4, "minLevel": "intermediate"},
                {"skillId": "typescript", "order": 5, "minLevel": "intermediate"}
            ],
            "estimatedWeeks": 16,
            "difficulty": "intermediate",
            "createdAt": datetime.utcnow()
        },
        {
            "roleId": "backend-developer",
            "title": "Backend Developer",
            "description": "Comprehensive backend development learning path",
            "skills": [
                {"skillId": "python", "order": 1, "minLevel": "intermediate"},
                {"skillId": "sql", "order": 2, "minLevel": "intermediate"},
                {"skillId": "flask", "order": 3, "minLevel": "intermediate"},
                {"skillId": "postgresql", "order": 4, "minLevel": "intermediate"},
                {"skillId": "docker", "order": 5, "minLevel": "beginner"}
            ],
            "estimatedWeeks": 18,
            "difficulty": "intermediate",
            "createdAt": datetime.utcnow()
        },
        {
            "roleId": "fullstack-developer",
            "title": "Full Stack Developer",
            "description": "End-to-end web development skills",
            "skills": [
                {"skillId": "html", "order": 1, "minLevel": "intermediate"},
                {"skillId": "css", "order": 2, "minLevel": "intermediate"},
                {"skillId": "javascript", "order": 3, "minLevel": "advanced"},
                {"skillId": "react", "order": 4, "minLevel": "intermediate"},
                {"skillId": "nodejs", "order": 5, "minLevel": "intermediate"},
                {"skillId": "express", "order": 6, "minLevel": "intermediate"},
                {"skillId": "mongodb", "order": 7, "minLevel": "beginner"}
            ],
            "estimatedWeeks": 24,
            "difficulty": "advanced",
            "createdAt": datetime.utcnow()
        },
        {
            "roleId": "data-scientist",
            "title": "Data Scientist",
            "description": "Data science and machine learning expertise",
            "skills": [
                {"skillId": "python", "order": 1, "minLevel": "advanced"},
                {"skillId": "pandas", "order": 2, "minLevel": "intermediate"},
                {"skillId": "sql", "order": 3, "minLevel": "intermediate"},
                {"skillId": "machine-learning", "order": 4, "minLevel": "intermediate"},
                {"skillId": "tensorflow", "order": 5, "minLevel": "beginner"}
            ],
            "estimatedWeeks": 20,
            "difficulty": "advanced",
            "createdAt": datetime.utcnow()
        },
        {
            "roleId": "devops-engineer",
            "title": "DevOps Engineer",
            "description": "Infrastructure and deployment automation",
            "skills": [
                {"skillId": "docker", "order": 1, "minLevel": "intermediate"},
                {"skillId": "kubernetes", "order": 2, "minLevel": "intermediate"},
                {"skillId": "aws", "order": 3, "minLevel": "intermediate"},
                {"skillId": "python", "order": 4, "minLevel": "beginner"}
            ],
            "estimatedWeeks": 16,
            "difficulty": "advanced",
            "createdAt": datetime.utcnow()
        }
    ]
    
    return templates_data

def seed_learning_resources():
    """Seed learning resources for skills"""
    
    resources_data = [
        # JavaScript Resources
        {
            "skillId": "javascript",
            "title": "JavaScript: The Complete Guide",
            "provider": "Udemy",
            "level": "beginner",
            "type": "course",
            "url": "https://www.udemy.com/course/javascript-the-complete-guide-2020-beginner-advanced/",
            "duration": "52h",
            "rating": 4.6,
            "verified": True
        },
        {
            "skillId": "javascript",
            "title": "MDN JavaScript Guide",
            "provider": "Mozilla",
            "level": "intermediate",
            "type": "documentation",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
            "duration": "Self-paced",
            "rating": 4.8,
            "verified": True
        },
        
        # React Resources
        {
            "skillId": "react",
            "title": "React - The Complete Guide",
            "provider": "Udemy",
            "level": "beginner",
            "type": "course",
            "url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/",
            "duration": "48h",
            "rating": 4.7,
            "verified": True
        },
        {
            "skillId": "react",
            "title": "Official React Documentation",
            "provider": "React Team",
            "level": "intermediate",
            "type": "documentation",
            "url": "https://react.dev/",
            "duration": "Self-paced",
            "rating": 4.9,
            "verified": True
        },
        
        # Python Resources
        {
            "skillId": "python",
            "title": "Python for Everybody Specialization",
            "provider": "Coursera",
            "level": "beginner",
            "type": "course",
            "url": "https://www.coursera.org/specializations/python",
            "duration": "32h",
            "rating": 4.8,
            "verified": True
        },
        {
            "skillId": "python",
            "title": "Automate the Boring Stuff with Python",
            "provider": "No Starch Press",
            "level": "beginner",
            "type": "book",
            "url": "https://automatetheboringstuff.com/",
            "duration": "Self-paced",
            "rating": 4.7,
            "verified": True
        },
        
        # Docker Resources
        {
            "skillId": "docker",
            "title": "Docker Mastery: with Kubernetes +Swarm",
            "provider": "Udemy",
            "level": "intermediate",
            "type": "course",
            "url": "https://www.udemy.com/course/docker-mastery/",
            "duration": "19h",
            "rating": 4.6,
            "verified": True
        },
        {
            "skillId": "docker",
            "title": "Official Docker Documentation",
            "provider": "Docker Inc.",
            "level": "beginner",
            "type": "documentation",
            "url": "https://docs.docker.com/",
            "duration": "Self-paced",
            "rating": 4.5,
            "verified": True
        },
        
        # Machine Learning Resources
        {
            "skillId": "machine-learning",
            "title": "Machine Learning Course",
            "provider": "Coursera (Stanford)",
            "level": "intermediate",
            "type": "course",
            "url": "https://www.coursera.org/learn/machine-learning",
            "duration": "60h",
            "rating": 4.9,
            "verified": True
        },
        {
            "skillId": "machine-learning",
            "title": "Hands-On Machine Learning",
            "provider": "O'Reilly",
            "level": "intermediate",
            "type": "book",
            "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781492032632/",
            "duration": "Self-paced",
            "rating": 4.8,
            "verified": True
        }
    ]
    
    return resources_data

def main():
    """Main seeding function"""
    print("🌱 Starting SkillBridge Suite database seeding...")
    
    try:
        # Initialize Firestore service
        db_service = FirestoreService()
        
        # Seed skills master data
        print("\n📚 Seeding skills master data...")
        skills_data = seed_skills_master()
        
        for skill in skills_data:
            skill_id = skill['skillId']
            success = db_service.create_document('skills_master', skill_id, skill)
            if success:
                print(f"  ✅ Created skill: {skill['name']}")
            else:
                print(f"  ❌ Failed to create skill: {skill['name']}")
        
        print(f"\n✅ Seeded {len(skills_data)} skills")
        
        # Seed roadmap templates
        print("\n🗺️  Seeding roadmap templates...")
        templates_data = seed_roadmap_templates()
        
        for template in templates_data:
            template_id = template['roleId']
            success = db_service.create_document('roadmap_templates', template_id, template)
            if success:
                print(f"  ✅ Created template: {template['title']}")
            else:
                print(f"  ❌ Failed to create template: {template['title']}")
        
        print(f"\n✅ Seeded {len(templates_data)} roadmap templates")
        
        # Seed learning resources
        print("\n📖 Seeding learning resources...")
        resources_data = seed_learning_resources()
        
        for i, resource in enumerate(resources_data):
            resource_id = f"resource_{i+1}"
            success = db_service.create_document('learning_resources', resource_id, resource)
            if success:
                print(f"  ✅ Created resource: {resource['title']}")
            else:
                print(f"  ❌ Failed to create resource: {resource['title']}")
        
        print(f"\n✅ Seeded {len(resources_data)} learning resources")
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nYour SkillBridge Suite backend is now ready with:")
        print(f"  • {len(skills_data)} technical and soft skills")
        print(f"  • {len(templates_data)} career roadmap templates")
        print(f"  • {len(resources_data)} curated learning resources")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()