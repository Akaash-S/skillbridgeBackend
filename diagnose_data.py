#!/usr/bin/env python3
"""
Diagnostic script to check Firestore data quality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.firestore import FirestoreService
import json

def diagnose_firestore_data():
    """Diagnose Firestore data quality issues"""
    print("🔍 Diagnosing Firestore Data Quality")
    print("=" * 50)
    
    db_service = FirestoreService()
    
    # Check skills_master collection
    print("\n📚 Skills Master Collection:")
    skills = db_service.query_collection('skills_master')
    print(f"  Total skills: {len(skills)}")
    
    # Check for null IDs
    null_id_skills = [s for s in skills if not s.get('skillId')]
    if null_id_skills:
        print(f"  ❌ Skills with null IDs: {len(null_id_skills)}")
        for skill in null_id_skills[:5]:  # Show first 5
            print(f"    - {skill.get('name', 'Unknown')} (category: {skill.get('category', 'Unknown')})")
    
    # Check for duplicate skill IDs
    skill_ids = [s.get('skillId') for s in skills if s.get('skillId')]
    duplicate_ids = []
    seen_ids = set()
    for skill_id in skill_ids:
        if skill_id in seen_ids:
            duplicate_ids.append(skill_id)
        seen_ids.add(skill_id)
    
    if duplicate_ids:
        print(f"  ❌ Duplicate skill IDs: {len(set(duplicate_ids))}")
        for dup_id in set(duplicate_ids):
            print(f"    - {dup_id}")
    
    # Show sample skills
    print(f"\n  📋 Sample skills:")
    for skill in skills[:5]:
        print(f"    - ID: {skill.get('skillId', 'NULL')}, Name: {skill.get('name', 'Unknown')}, Category: {skill.get('category', 'Unknown')}")
    
    # Check job_roles collection
    print("\n💼 Job Roles Collection:")
    roles = db_service.query_collection('job_roles')
    print(f"  Total roles: {len(roles)}")
    
    # Show sample roles
    print(f"\n  📋 Sample roles:")
    for role in roles[:3]:
        required_skills = role.get('requiredSkills', [])
        print(f"    - ID: {role.get('roleId', 'NULL')}, Title: {role.get('title', 'Unknown')}")
        print(f"      Required skills: {len(required_skills)}")
        for skill in required_skills[:3]:
            print(f"        • {skill.get('skillId', 'NULL')} ({skill.get('minProficiency', 'unknown')})")
    
    # Check learning_resources collection
    print("\n📖 Learning Resources Collection:")
    resources = db_service.query_collection('learning_resources')
    print(f"  Total resources: {len(resources)}")
    
    # Check user_skills collection (should be empty for new setup)
    print("\n👤 User Skills Collection:")
    user_skills = db_service.query_collection('user_skills')
    print(f"  Total user skills: {len(user_skills)}")
    
    # Check user_roadmaps collection
    print("\n🗺️ User Roadmaps Collection:")
    roadmaps = db_service.query_collection('user_roadmaps')
    print(f"  Total roadmaps: {len(roadmaps)}")
    
    # Check roadmap_templates collection
    print("\n📋 Roadmap Templates Collection:")
    templates = db_service.query_collection('roadmap_templates')
    print(f"  Total templates: {len(templates)}")
    
    print("\n🎯 Recommendations:")
    if null_id_skills:
        print("  1. Fix skills with null IDs")
    if duplicate_ids:
        print("  2. Remove duplicate skill IDs")
    if len(skills) == 0:
        print("  1. Run seed_data_frontend.py to populate skills")
    if len(roles) == 0:
        print("  2. Run seed_data_frontend.py to populate roles")
    
    return len(null_id_skills) == 0 and len(duplicate_ids) == 0

if __name__ == "__main__":
    success = diagnose_firestore_data()
    sys.exit(0 if success else 1)