#!/usr/bin/env python3
"""Debug script to check document structure and IDs"""

from app.db.firestore import FirestoreService

def check_document_structure():
    db = FirestoreService()
    
    print("🔍 Checking document structure...")
    
    # Get all skills and check their document IDs vs skillId fields
    skills = db.query_collection('skills_master')
    
    print(f"📊 Total skills: {len(skills)}")
    
    # Look for aws-full specifically
    aws_full_docs = []
    for skill in skills:
        if skill.get('skillId') == 'aws-full':
            aws_full_docs.append(skill)
    
    print(f"\n🔍 Found {len(aws_full_docs)} documents with skillId='aws-full':")
    for i, doc in enumerate(aws_full_docs):
        print(f"  Document {i+1}:")
        print(f"    skillId: '{doc.get('skillId')}'")
        print(f"    name: '{doc.get('name')}'")
        print(f"    document keys: {list(doc.keys())}")
        
        # Check if there's a document ID field
        if 'id' in doc:
            print(f"    document id field: '{doc.get('id')}'")
    
    # Try different ways to get the document
    print(f"\n🧪 Testing different document retrieval methods:")
    
    # Method 1: Direct get with skillId
    doc1 = db.get_document('skills_master', 'aws-full')
    print(f"  get_document('skills_master', 'aws-full'): {doc1 is not None}")
    
    # Method 2: Check if there's a different document ID
    # Let's see what the actual Firestore document IDs are
    print(f"\n📋 First 5 skills with their internal structure:")
    for i, skill in enumerate(skills[:5]):
        print(f"  {i+1}. skillId: '{skill.get('skillId')}', name: '{skill.get('name')}'")
        print(f"      All fields: {skill}")
        print()

if __name__ == "__main__":
    check_document_structure()