import os
import re

collections = set()
pattern = re.compile(r'collection\s*\(\s*[\'"]([^\'"]+)[\'"]')
# Also find create_document, get_document, etc calls in FirestoreService
firestore_call_pattern = re.compile(r'(?:create_document|get_document|update_document|delete_document|query_documents|get_all_documents|list_documents)\s*\(\s*[\'"]([^\'"]+)[\'"]')

target_dir = 'app' if os.path.exists('app') else 'backend'
for root, _, files in os.walk(target_dir):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
                for match in pattern.finditer(content):
                    collections.add(match.group(1))
                for match in firestore_call_pattern.finditer(content):
                    collections.add(match.group(1))

print(f"Total collections found: {len(collections)}")
for c in sorted(collections):
    print("-", c)
