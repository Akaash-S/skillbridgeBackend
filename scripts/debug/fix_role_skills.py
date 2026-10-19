#!/usr/bin/env python3
"""
Fix job role skill references after cleaning up skills
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.firestore import FirestoreService
from datetime import datetime

def fix_role_skill_references():
    """Fix job role skill references to use correct skill IDs"""
    print("🔧 Fixing Job Role Skill References")
    print("=" * 45)
    
    db_service = FirestoreService()
    
    # Mapping of old skill IDs to new ones
    skill_id_mapping = {
        'js': 'javascript',
        'ts': 'typescript', 
        'ml': 'machine-learning',
        'problemsolving': 'problem-solving'
    }
    
    # Get all job roles
    roles = db_service.query_collection('job_roles')
    print(f"💼 Found {len(roles)} job roles")
    
    fixed_roles = 0
    for role in roles:
        role_id = role.get('id')
        role_title = role.get('title', 'Unknown')
        required_skills = role.get('requiredSkills', [])
        
        if not role_id:
            print(f"  ❌ Role '{role_title}' has no document ID")
            continue
        
        # Check if any skills need updating
        needs_update = False
        updated_skills = []
        
        for skill_req in required_skills:
            old_skill_id = skill_req.get('skillId')
            new_skill_id = skill_id_mapping.get(old_skill_id, old_skill_id)
            
            if new_skill_id != old_skill_id:
                needs_update = True
                print(f"    🔄 {role_title}: {old_skill_id} -> {new_skill_id}")
            
            updated_skills.append({
                'skillId': new_skill_id,
                'minProficiency': skill_req.get('minProficiency', 'intermediate')
            })
        
        if needs_update:
            # Update the role
            update_data = {
                'requiredSkills': updated_skills,
                'updatedAt': datetime.utcnow()
            }
            
            success = db_service.update_document('job_roles', role_id, update_data)
            if success:
                print(f"  ✅ Updated role: {role_title}")
                fixed_roles += 1
            else:
                print(f"  ❌ Failed to update role: {role_title}")
        else:
            print(f"  ✅ Role '{role_title}' already has correct skill IDs")
    
    print(f"\n🎉 Fixed {fixed_roles} job roles")
    
    # Verify all skill references are valid
    print(f"\n🔍 Verifying skill references...")
    
    # Get all valid skill IDs
    skills = db_service.query_collection('skills_master')
    valid_skill_ids = set(s.get('skillId') for s in skills if s.get('skillId'))
    print(f"  📚 Found {len(valid_skill_ids)} valid skill IDs")
    
    # Check all role skill references
    roles = db_service.query_collection('job_roles')  # Refresh data
    invalid_references = []
    
    for role in roles:
        role_title = role.get('title', 'Unknown')
        required_skills = role.get('requiredSkills', [])
        
        for skill_req in required_skills:
            skill_id = skill_req.get('skillId')
            if skill_id not in valid_skill_ids:
                invalid_references.append(f"{role_title} -> {skill_id}")
    
    if invalid_references:
        print(f"  ❌ Found {len(invalid_references)} invalid skill references:")
        for ref in invalid_references:
            print(f"    - {ref}")
    else:
        print(f"  ✅ All skill references are valid!")
    
    return len(invalid_references) == 0

if __name__ == "__main__":
    success = fix_role_skill_references()
    sys.exit(0 if success else 1)