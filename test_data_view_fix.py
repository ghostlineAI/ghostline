#!/usr/bin/env python3
"""
Test script to verify data view functionality is working correctly.
Tests VIEW (content proxy) and DOWNLOAD (forced download) endpoints.
"""

import requests
import time
import os

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.dev.ghostline.ai/api/v1")
TEST_EMAIL = f"dataview-test-{int(time.time())}@example.com"
TEST_PASSWORD = "testpassword123"

print(f"Testing data view functionality against: {API_BASE_URL}")

# Step 1: Register/Login
print("\n1. Creating test user...")
timestamp = int(time.time())
register_response = requests.post(
    f"{API_BASE_URL}/auth/register",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "username": f"dataviewtest{timestamp}"
    }
)

if register_response.status_code == 200:
    print(f"✅ User created successfully")
    
    # Now login to get token
    login_response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if login_response.status_code == 200:
        auth_data = login_response.json()
        token = auth_data.get("access_token") or auth_data.get("token")
        if not token:
            print(f"❌ No token in login response: {auth_data}")
            exit(1)
        print(f"✅ Logged in successfully")
    else:
        print(f"❌ Failed to login: {login_response.status_code}")
        print(login_response.text)
        exit(1)
else:
    print(f"❌ Failed to create user: {register_response.status_code}")
    print(register_response.text)
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Create project
print("\n2. Creating test project...")
project_response = requests.post(
    f"{API_BASE_URL}/projects/",
    json={
        "title": f"Data View Test {int(time.time())}",
        "description": "Test project for data view",
        "genre": "fiction"
    },
    headers=headers
)

if project_response.status_code != 200:
    print(f"❌ Failed to create project: {project_response.status_code}")
    exit(1)

project_id = project_response.json()["id"]
print(f"✅ Project created: {project_id}")

# Step 3: Upload test file
print("\n3. Uploading test file...")
test_content = "This is test content for data view functionality"
files = {"file": ("test.txt", test_content, "text/plain")}
data = {"project_id": project_id}

upload_response = requests.post(
    f"{API_BASE_URL}/source-materials/upload",
    files=files,
    data=data,
    headers=headers
)

if upload_response.status_code != 200:
    print(f"❌ Upload failed: {upload_response.status_code}")
    print(upload_response.text)
    exit(1)

material_id = upload_response.json()["id"]
print(f"✅ File uploaded: {material_id}")

# Step 4: Test VIEW functionality (content proxy - no CORS)
print("\n4. Testing VIEW functionality (content proxy)...")
content_url = f"{API_BASE_URL}/source-materials/{material_id}/content"
print(f"   Calling: {content_url}")
content_response = requests.get(content_url, headers=headers)

if content_response.status_code == 200:
    if content_response.text == test_content:
        print("✅ VIEW working correctly - content matches!")
    else:
        print("⚠️  VIEW returned content but it doesn't match")
    print(f"   Content-Type: {content_response.headers.get('content-type')}")
    print(f"   Cache-Control: {content_response.headers.get('cache-control')}")
else:
    print(f"❌ VIEW failed: {content_response.status_code}")
    print(content_response.text)

# Step 5: Test DOWNLOAD functionality (forced download)
print("\n5. Testing DOWNLOAD functionality...")
download_url = f"{API_BASE_URL}/source-materials/{material_id}/download"
print(f"   Calling: {download_url}")
download_response = requests.get(download_url, headers=headers)

if download_response.status_code == 200:
    content_disposition = download_response.headers.get('content-disposition', '')
    if 'attachment' in content_disposition and 'test.txt' in content_disposition:
        print("✅ DOWNLOAD working correctly - proper headers!")
        print(f"   Content-Disposition: {content_disposition}")
    else:
        print("⚠️  DOWNLOAD returned content but headers are wrong")
        print(f"   Content-Disposition: {content_disposition}")
    
    if download_response.content.decode() == test_content:
        print("✅ Downloaded content matches!")
else:
    print(f"❌ DOWNLOAD failed: {download_response.status_code}")
    print(download_response.text)

# Step 6: Test old download-url endpoint still works
print("\n6. Testing legacy download-url endpoint...")
url_response = requests.get(
    f"{API_BASE_URL}/source-materials/{material_id}/download-url",
    headers=headers
)

if url_response.status_code == 200:
    data = url_response.json()
    if "download_url" in data:
        print("✅ Legacy download-url endpoint still working")
        print(f"   URL: {data['download_url'][:100]}...")
else:
    print(f"⚠️  Legacy endpoint failed: {url_response.status_code}")

# Step 7: Cleanup
print("\n7. Cleaning up...")
delete_response = requests.delete(
    f"{API_BASE_URL}/source-materials/{material_id}",
    headers=headers
)

if delete_response.status_code == 200:
    print("✅ Cleanup successful")
else:
    print(f"⚠️  Cleanup failed: {delete_response.status_code}")

print("\n✅ All data view functionality tests completed!") 