#!/usr/bin/env python3
"""Debug script to check skills in database"""

from app.db.firestore import FirestoreService

def check_skills_database():
    db = FirestoreService()
    
    print("🔍 Checking skills_master collection...")
    skills = db.query_collection('skills_master')
    
    print(f"📊 Total skills in database: {len(skills)}")
    
    if skills:
        print("\n📋 First 10 skills with IDs:")
        for i, skill in enumerate(skills[:10]):
            print(f"  {i+1}. ID: '{skill.get('skillId')}', Name: '{skill.get('name')}'")
        
        print("\n🔍 All skill IDs (for frontend reference):")
        skill_ids = [skill.get('skillId') for skill in skills]
        print(f"  {skill_ids}")
    else:
        print("❌ No skills found in skills_master collection!")
        
        # Check if collection exists but is empty
        print("\n🔍 Checking all collections...")
        try:
            # This is a simplified check - in production you'd use proper Firestore admin methods
            print("Collections might be empty or not seeded yet.")
        except Exception as e:
            print(f"Error checking collections: {e}")
    
    return len(skills) > 0

if __name__ == "__main__":
    has_skills = check_skills_database()
    
    if not has_skills:
        print("\n💡 Suggestion: Run the seed_data_frontend.py script to populate the database")
        print("   Command: python seed_data_frontend.py")