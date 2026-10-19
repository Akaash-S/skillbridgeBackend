#!/usr/bin/env python3
"""
Fix data quality issues in Firestore
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.firestore import FirestoreService
from datetime import datetime

def fix_data_issues():
    """Fix known data quality issues"""
    print("🔧 Fixing Firestore Data Issues")
    print("=" * 40)
    
    db_service = FirestoreService()
    
    # Get all skills
    skills = db_service.query_collection('skills_master')
    print(f"📚 Found {len(skills)} skills")
    
    # Fix skills with null IDs
    null_id_skills = [s for s in skills if not s.get('skillId')]
    print(f"🔍 Found {len(null_id_skills)} skills with null IDs")
    
    fixed_count = 0
    for skill in null_id_skills:
        skill_name = skill.get('name', '')
        skill_id = skill.get('id')  # Document ID from Firestore
        
        if not skill_id:
            print(f"  ❌ Cannot fix skill '{skill_name}' - no document ID")
            continue
        
        # Generate skillId based on name
        if skill_name == "Amazon Web Services":
            new_skill_id = "aws-full"  # Use different ID to avoid conflict with existing "aws"
        elif skill_name == "Node.js":
            new_skill_id = "nodejs-alt"  # Use different ID to avoid conflict with existing "nodejs"
        else:
            # Generate ID from name
            new_skill_id = skill_name.lower().replace(' ', '-').replace('.', '').replace('/', '-')
        
        # Update the skill with proper skillId
        update_data = {
            'skillId': new_skill_id,
            'updatedAt': datetime.utcnow()
        }
        
        success = db_service.update_document('skills_master', skill_id, update_data)
        if success:
            print(f"  ✅ Fixed skill '{skill_name}' -> ID: {new_skill_id}")
            fixed_count += 1
        else:
            print(f"  ❌ Failed to fix skill '{skill_name}'")
    
    # Remove duplicate skills (keep the one with better ID)
    print(f"\n🔍 Checking for duplicate skills...")
    
    # Group skills by name
    skills_by_name = {}
    for skill in skills:
        name = skill.get('name', '').lower()
        if name not in skills_by_name:
            skills_by_name[name] = []
        skills_by_name[name].append(skill)
    
    # Find duplicates
    duplicates_removed = 0
    for name, skill_list in skills_by_name.items():
        if len(skill_list) > 1:
            print(f"  🔍 Found {len(skill_list)} skills named '{name}'")
            
            # Sort by preference (prefer skills with proper skillId)
            skill_list.sort(key=lambda s: (
                s.get('skillId') is not None,  # Prefer non-null skillId
                len(s.get('skillId', '')),     # Prefer shorter IDs
                s.get('skillId', '')           # Alphabetical
            ), reverse=True)
            
            # Keep the first (best) one, remove others
            keep_skill = skill_list[0]
            remove_skills = skill_list[1:]
            
            print(f"    ✅ Keeping: {keep_skill.get('skillId', 'NULL')} - {keep_skill.get('name')}")
            
            for remove_skill in remove_skills:
                skill_id = remove_skill.get('id')
                if skill_id:
                    success = db_service.delete_document('skills_master', skill_id)
                    if success:
                        print(f"    🗑️ Removed: {remove_skill.get('skillId', 'NULL')} - {remove_skill.get('name')}")
                        duplicates_removed += 1
                    else:
                        print(f"    ❌ Failed to remove: {remove_skill.get('skillId', 'NULL')} - {remove_skill.get('name')}")
    
    print(f"\n🎉 Data fixing completed!")
    print(f"  • Fixed {fixed_count} skills with null IDs")
    print(f"  • Removed {duplicates_removed} duplicate skills")
    
    # Run diagnosis again
    print(f"\n🔍 Running diagnosis again...")
    from diagnose_data import diagnose_firestore_data
    return diagnose_firestore_data()

if __name__ == "__main__":
    success = fix_data_issues()
    sys.exit(0 if success else 1)