#!/usr/bin/env python3
"""Test PRODUCTION API to verify real S3 uploads."""

import requests
import time
from pathlib import Path

# PRODUCTION API
API_BASE_URL = "https://api.dev.ghostline.ai/api/v1"

print("🚀 TESTING PRODUCTION API - REAL S3 UPLOADS")
print("=" * 60)
print(f"API URL: {API_BASE_URL}")

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

# Login
print("\n1️⃣ Logging in...")
login_response = requests.post(
    f"{API_BASE_URL}/auth/login",
    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(f"Response: {login_response.text}")
    exit(1)

auth_data = login_response.json()
headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
print("✅ Logged in successfully")

# Get or create project
print("\n2️⃣ Getting projects...")
projects_response = requests.get(f"{API_BASE_URL}/projects", headers=headers)
projects = projects_response.json()

if not projects:
    print("Creating new project...")
    project_data = {
        "title": "S3 Production Test",
        "genre": "fiction",
        "description": "Testing real S3 uploads in production"
    }
    create_response = requests.post(f"{API_BASE_URL}/projects", headers=headers, json=project_data)
    if create_response.status_code == 200:
        project = create_response.json()
        project_id = project["id"]
        print(f"✅ Created project: {project_id}")
    else:
        print(f"❌ Failed to create project: {create_response.status_code}")
        exit(1)
else:
    project_id = projects[0]["id"]
    print(f"✅ Using existing project: {project_id}")

# Create unique test file
timestamp = int(time.time())
test_filename = f"production_s3_test_{timestamp}.txt"
test_content = f"""PRODUCTION S3 TEST FILE
Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}
Timestamp: {timestamp}
Testing real S3 uploads in production environment
This file should be uploaded to: ghostline-dev-source-materials-820242943150
"""

with open(test_filename, "w") as f:
    f.write(test_content)

print(f"\n3️⃣ Uploading file: {test_filename}")

# Upload the file
try:
    with open(test_filename, "rb") as f:
        files = {"file": (test_filename, f, "text/plain")}
        data = {"project_id": project_id}
        
        upload_response = requests.post(
            f"{API_BASE_URL}/source-materials/upload",
            headers=headers,
            files=files,
            data=data
        )
    
    print(f"\n📋 Upload Response:")
    print(f"   Status Code: {upload_response.status_code}")
    
    if upload_response.status_code == 200:
        upload_data = upload_response.json()
        print(f"   ✅ UPLOAD SUCCESSFUL!")
        print(f"   File ID: {upload_data.get('id')}")
        print(f"   Filename: {upload_data.get('name', upload_data.get('filename'))}")
        
        # Check if it's mock or real
        if upload_data.get('mock'):
            print("\n   ⚠️  WARNING: Production is still using MOCK S3!")
        else:
            print("\n   ✅ Production is using REAL S3!")
            
        # Wait and check S3
        print(f"\n4️⃣ Checking S3 bucket...")
        time.sleep(2)
        
        import subprocess
        result = subprocess.run(
            ["aws", "s3", "ls", "s3://ghostline-dev-source-materials-820242943150/source-materials/", "--recursive"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and test_filename in result.stdout:
            print(f"   ✅ FILE FOUND IN S3!")
        else:
            print(f"   ⚠️  File not found in S3 yet")
            
    else:
        print(f"   ❌ Upload failed")
        print(f"   Response: {upload_response.text[:500]}")
        
finally:
    # Clean up
    Path(test_filename).unlink(missing_ok=True)
    print(f"\n🧹 Cleaned up test file")

print("\n" + "=" * 60)
print("✅ PRODUCTION TEST COMPLETE") 