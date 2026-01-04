#!/usr/bin/env python3
"""
SkillBridge Suite API Testing Script
Tests all major API endpoints to ensure they're working correctly
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TOKEN = None  # Will be set after login test

def print_test_result(test_name, success, message=""):
    """Print formatted test results"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")

def test_health_check():
    """Test health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        success = response.status_code == 200
        message = f"Status: {response.status_code}"
        if success:
            data = response.json()
            message += f", Service: {data.get('service', 'unknown')}"
        print_test_result("Health Check", success, message)
        return success
    except Exception as e:
        print_test_result("Health Check", False, f"Error: {str(e)}")
        return False

def test_skills_master():
    """Test skills master endpoint (no auth required)"""
    try:
        response = requests.get(f"{BASE_URL}/skills?type=master", timeout=10)
        success = response.status_code in [200, 401]  # 401 is expected without auth
        message = f"Status: {response.status_code}"
        print_test_result("Skills Master Endpoint", success, message)
        return success
    except Exception as e:
        print_test_result("Skills Master Endpoint", False, f"Error: {str(e)}")
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    # Test login endpoint (should fail without valid token)
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"idToken": "invalid_token"},
            timeout=10
        )
        success = response.status_code in [400, 401]  # Expected to fail
        message = f"Status: {response.status_code}"
        print_test_result("Auth Login Endpoint", success, message)
        return success
    except Exception as e:
        print_test_result("Auth Login Endpoint", False, f"Error: {str(e)}")
        return False

def test_jobs_search():
    """Test jobs search endpoint (no auth required)"""
    try:
        response = requests.get(
            f"{BASE_URL}/jobs/search?role=software engineer&limit=5",
            timeout=15
        )
        success = response.status_code == 200
        message = f"Status: {response.status_code}"
        if success:
            data = response.json()
            job_count = len(data.get('results', {}).get('jobs', []))
            message += f", Jobs found: {job_count}"
        print_test_result("Jobs Search", success, message)
        return success
    except Exception as e:
        print_test_result("Jobs Search", False, f"Error: {str(e)}")
        return False

def test_jobs_trending():
    """Test trending jobs endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/jobs/trending", timeout=15)
        success = response.status_code == 200
        message = f"Status: {response.status_code}"
        if success:
            data = response.json()
            roles_count = len(data.get('trendingRoles', []))
            message += f", Trending roles: {roles_count}"
        print_test_result("Trending Jobs", success, message)
        return success
    except Exception as e:
        print_test_result("Trending Jobs", False, f"Error: {str(e)}")
        return False

def test_jobs_countries():
    """Test supported countries endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/jobs/countries", timeout=10)
        success = response.status_code == 200
        message = f"Status: {response.status_code}"
        if success:
            data = response.json()
            countries_count = len(data.get('countries', []))
            message += f", Countries: {countries_count}"
        print_test_result("Supported Countries", success, message)
        return success
    except Exception as e:
        print_test_result("Supported Countries", False, f"Error: {str(e)}")
        return False

def test_cors_headers():
    """Test CORS headers"""
    try:
        response = requests.options(f"{BASE_URL}/health", timeout=5)
        success = response.status_code in [200, 204]
        message = f"Status: {response.status_code}"
        
        # Check for CORS headers
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]
        
        found_headers = []
        for header in cors_headers:
            if header in response.headers:
                found_headers.append(header)
        
        if found_headers:
            message += f", CORS headers: {len(found_headers)}/{len(cors_headers)}"
        
        print_test_result("CORS Headers", success, message)
        return success
    except Exception as e:
        print_test_result("CORS Headers", False, f"Error: {str(e)}")
        return False

def test_protected_endpoints():
    """Test that protected endpoints require authentication"""
    protected_endpoints = [
        "/users/profile",
        "/skills",
        "/roadmap",
        "/learning/recommendations",
        "/activity",
        "/settings"
    ]
    
    all_protected = True
    
    for endpoint in protected_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            is_protected = response.status_code == 401
            
            if not is_protected:
                all_protected = False
            
            status = "Protected" if is_protected else "Unprotected"
            print(f"    {endpoint}: {status} ({response.status_code})")
            
        except Exception as e:
            print(f"    {endpoint}: Error - {str(e)}")
            all_protected = False
    
    print_test_result("Protected Endpoints", all_protected)
    return all_protected

def run_all_tests():
    """Run all API tests"""
    print("🧪 SkillBridge Suite API Testing")
    print("=" * 40)
    print(f"Testing API at: {BASE_URL}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Health Check", test_health_check),
        ("Skills Endpoints", test_skills_master),
        ("Authentication", test_auth_endpoints),
        ("Jobs Search", test_jobs_search),
        ("Trending Jobs", test_jobs_trending),
        ("Supported Countries", test_jobs_countries),
        ("CORS Configuration", test_cors_headers),
        ("Endpoint Protection", test_protected_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print_test_result(test_name, False, f"Unexpected error: {str(e)}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your API is working correctly.")
        return True
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the issues above.")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        global BASE_URL
        BASE_URL = sys.argv[1]
    
    success = run_all_tests()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()