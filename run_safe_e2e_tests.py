#!/usr/bin/env python3
"""
SAFE E2E Test Runner for GhostLine API
This script runs E2E tests against the production API without any database connection.
It will NEVER drop tables or modify the database directly.
"""

import requests
import json
import time
import uuid
from datetime import datetime

# Production API URL
API_URL = "https://api.dev.ghostline.ai/api/v1"

# Test data
test_email = f"e2e_test_{uuid.uuid4().hex[:8]}@example.com"
test_username = f"e2e_test_{uuid.uuid4().hex[:8]}"
test_password = "TestPassword123!"

print("🧪 SAFE E2E Test Runner for GhostLine API")
print("=" * 50)
print(f"API URL: {API_URL}")
print(f"Test Email: {test_email}")
print("\n⚠️  This script will NEVER connect directly to the database")
print("✅ All tests run through the API only\n")

# Track test results
results = []

def test_api_health():
    """Test 1: API Health Check"""
    print("1️⃣ Testing API Health...")
    try:
        response = requests.get(f"{API_URL.replace('/api/v1', '')}/health")
        if response.status_code == 200:
            print("✅ API is healthy")
            results.append(("API Health", True, ""))
        else:
            print(f"❌ API health check failed: {response.status_code}")
            results.append(("API Health", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"❌ API health check error: {e}")
        results.append(("API Health", False, str(e)))

def test_user_registration():
    """Test 2: User Registration"""
    print("\n2️⃣ Testing User Registration...")
    try:
        data = {
            "email": test_email,
            "username": test_username,
            "password": test_password,
            "full_name": "E2E Test User"
        }
        response = requests.post(f"{API_URL}/auth/register", json=data)
        if response.status_code == 200:
            print("✅ User registration successful")
            results.append(("User Registration", True, ""))
            return response.json()
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            results.append(("User Registration", False, f"{response.status_code}: {response.text}"))
            return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        results.append(("User Registration", False, str(e)))
        return None

def test_user_login():
    """Test 3: User Login"""
    print("\n3️⃣ Testing User Login...")
    try:
        data = {
            "email": test_email,
            "password": test_password
        }
        response = requests.post(f"{API_URL}/auth/login", json=data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ User login successful")
            results.append(("User Login", True, ""))
            return token
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            results.append(("User Login", False, f"{response.status_code}: {response.text}"))
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        results.append(("User Login", False, str(e)))
        return None

def test_project_creation(token):
    """Test 4: Project Creation"""
    print("\n4️⃣ Testing Project Creation...")
    if not token:
        print("⏭️  Skipping project creation (no auth token)")
        results.append(("Project Creation", False, "No auth token"))
        return None
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "title": f"E2E Test Project {int(time.time())}",
            "genre": "fiction",
            "description": "This is an E2E test project"
        }
        response = requests.post(f"{API_URL}/projects/", json=data, headers=headers)
        if response.status_code == 200:
            project = response.json()
            print(f"✅ Project created: {project.get('title')}")
            results.append(("Project Creation", True, ""))
            return project
        else:
            print(f"❌ Project creation failed: {response.status_code} - {response.text}")
            results.append(("Project Creation", False, f"{response.status_code}: {response.text}"))
            return None
    except Exception as e:
        print(f"❌ Project creation error: {e}")
        results.append(("Project Creation", False, str(e)))
        return None

def test_project_list(token):
    """Test 5: List Projects"""
    print("\n5️⃣ Testing Project List...")
    if not token:
        print("⏭️  Skipping project list (no auth token)")
        results.append(("Project List", False, "No auth token"))
        return
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/projects/", headers=headers)
        if response.status_code == 200:
            projects = response.json()
            print(f"✅ Listed {len(projects)} projects")
            results.append(("Project List", True, f"{len(projects)} projects"))
        else:
            print(f"❌ Project list failed: {response.status_code} - {response.text}")
            results.append(("Project List", False, f"{response.status_code}: {response.text}"))
    except Exception as e:
        print(f"❌ Project list error: {e}")
        results.append(("Project List", False, str(e)))

def print_summary():
    """Print test summary"""
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    for test_name, success, details in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details and not success:
            print(f"       {details}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} tests failed")
    
    return failed == 0

# Run tests
if __name__ == "__main__":
    # Test 1: API Health
    test_api_health()
    
    # Test 2: Registration (will fail if API has database issues)
    user = test_user_registration()
    
    # Test 3: Login
    token = None
    if user:
        token = test_user_login()
    
    # Test 4: Create Project
    project = None
    if token:
        project = test_project_creation(token)
    
    # Test 5: List Projects
    if token:
        test_project_list(token)
    
    # Summary
    success = print_summary()
    exit(0 if success else 1) 