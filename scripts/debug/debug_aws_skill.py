#!/usr/bin/env python3
"""Debug script to check aws-full skill specifically"""

from app.db.firestore import FirestoreService

def check_aws_skill():
    db = FirestoreService()
    
    print("🔍 Checking for 'aws-full' skill...")
    
    # Try to get the specific skill
    skill = db.get_document('skills_master', 'aws-full')
    
    if skill:
        print(f"✅ Found skill: {skill}")
    else:
        print("❌ Skill 'aws-full' not found!")
        
        print("\n🔍 Checking all AWS-related skills...")
        skills = db.query_collection('skills_master')
        aws_skills = []
        
        for s in skills:
            skill_id = s.get('skillId', '').lower()
            skill_name = s.get('name', '').lower()
            
            if 'aws' in skill_id or 'aws' in skill_name:
                aws_skills.append(s)
        
        if aws_skills:
            print(f"Found {len(aws_skills)} AWS-related skills:")
            for s in aws_skills:
                print(f"  ID: '{s.get('skillId')}', Name: '{s.get('name')}'")
        else:
            print("No AWS-related skills found!")
        
        print("\n🔍 Checking first 10 skills to verify database connection...")
        for i, skill in enumerate(skills[:10]):
            print(f"  {i+1}. ID: '{skill.get('skillId')}', Name: '{skill.get('name')}'")

if __name__ == "__main__":
    check_aws_skill()