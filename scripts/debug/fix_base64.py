#!/usr/bin/env python3
"""
Script to fix base64 padding and update .env file
"""

import os
import base64

def fix_base64_padding(data):
    """Add proper padding to base64 string"""
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return data

def main():
    # Read the current base64 from .env
    env_path = '.env'
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Find the base64 line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('FIREBASE_SERVICE_ACCOUNT_BASE64='):
            current_base64 = line.split('=', 1)[1]
            if current_base64:
                # Fix padding
                fixed_base64 = fix_base64_padding(current_base64)
                
                # Test if it's valid
                try:
                    decoded = base64.b64decode(fixed_base64)
                    print(f"✅ Base64 is valid after padding fix")
                    print(f"Original length: {len(current_base64)}")
                    print(f"Fixed length: {len(fixed_base64)}")
                    
                    # Update the line
                    lines[i] = f'FIREBASE_SERVICE_ACCOUNT_BASE64={fixed_base64}'
                    
                    # Write back to file
                    with open(env_path, 'w') as f:
                        f.write('\n'.join(lines))
                    
                    print(f"✅ Updated .env file with properly padded base64")
                    return
                    
                except Exception as e:
                    print(f"❌ Base64 is still invalid: {e}")
                    return
            else:
                print("❌ No base64 value found in .env")
                return
    
    print("❌ FIREBASE_SERVICE_ACCOUNT_BASE64 line not found in .env")

if __name__ == "__main__":
    main()