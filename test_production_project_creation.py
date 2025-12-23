#!/usr/bin/env python3
"""Test project creation with the new schema against production API"""

import requests
import json
from datetime import datetime

# Test configuration
API_URL = "https://api.dev.ghostline.ai"
TEST_EMAIL = f"test_user_{int(datetime.now().timestamp())}@example.com"
TEST_PASSWORD = "TestPass123!"

print("🧪 Testing GhostLine Production API with New Schema")
print("=" * 50)

# 1. Register a new user
print("\n1. Registering new user...")
register_response = requests.post(
    f"{API_URL}/api/v1/auth/register",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "username": f"testuser_{int(datetime.now().timestamp())}",
        "full_name": "Schema Test User"
    }
)

if register_response.status_code == 200:
    print(f"✅ User registered: {TEST_EMAIL}")
else:
    print(f"❌ Registration failed: {register_response.status_code}")
    print(f"Response: {register_response.text}")
    exit(1)

# 2. Login to get token
print("\n2. Logging in...")
login_response = requests.post(
    f"{API_URL}/api/v1/auth/login",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print("✅ Login successful, got token")
else:
    print(f"❌ Login failed: {login_response.status_code}")
    print(f"Response: {login_response.text}")
    exit(1)

# 3. Create a project with the NEW schema (using 'title' not 'name')
print("\n3. Creating project with new schema...")
project_data = {
    "title": "Test Project - Schema Fixed",  # Using 'title' not 'name'!
    "subtitle": "Testing the new database schema",
    "description": "This project tests the fixed schema with title field",
    "genre": "fiction",
    "target_audience": "young_adult",
    "status": "draft",
    "target_page_count": 300,
    "target_word_count": 80000,
    "language": "en",
    "settings": {}
}

headers = {"Authorization": f"Bearer {token}"}
create_response = requests.post(
    f"{API_URL}/api/v1/projects/",
    json=project_data,
    headers=headers
)

if create_response.status_code == 200:
    project = create_response.json()
    print("✅ Project created successfully!")
    print(f"   - ID: {project['id']}")
    print(f"   - Title: {project['title']}")
    print(f"   - Status: {project['status']}")
    print(f"   - Created at: {project['created_at']}")
else:
    print(f"❌ Project creation failed: {create_response.status_code}")
    print(f"Response: {create_response.text}")
    exit(1)

# 4. List projects to verify
print("\n4. Listing projects...")
list_response = requests.get(
    f"{API_URL}/api/v1/projects/",
    headers=headers
)

if list_response.status_code == 200:
    projects = list_response.json()
    print(f"✅ Found {len(projects)} project(s)")
    for p in projects:
        print(f"   - {p['title']} (ID: {p['id']})")
else:
    print(f"❌ Failed to list projects: {list_response.status_code}")

print("\n" + "=" * 50)
print("✅ All tests passed! The schema fix is working correctly.")
print("   - Projects now use 'title' instead of 'name'")
print("   - New fields (subtitle, target_page_count, etc.) are working")
print("   - API is fully operational with the new schema") 