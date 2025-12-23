#!/usr/bin/env python3
"""
Test to reproduce the 503 error that the user is reporting
"""
import requests
import io
import time

API_URL = "https://api.dev.ghostline.ai/api/v1"

# Test credentials
email = "alexgrgs2314@gmail.com"
password = "lightlight2"

print("🔍 Testing for 503 'File upload service is temporarily unavailable' error")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Step 1: Check API health
print("\n1️⃣ Checking API health...")
try:
    health_response = requests.get(f"{API_URL.replace('/api/v1', '')}/health", timeout=10)
    print(f"   Health check: {health_response.status_code}")
    if health_response.status_code == 200:
        print(f"   Response: {health_response.json()}")
    else:
        print(f"   Response: {health_response.text}")
except Exception as e:
    print(f"   ❌ Health check failed: {e}")

# Step 2: Try to login
print("\n2️⃣ Attempting login...")
try:
    login_response = requests.post(
        f"{API_URL}/auth/login/",
        json={"email": email, "password": password},
        timeout=10
    )
    print(f"   Login status: {login_response.status_code}")
    if login_response.status_code == 200:
        auth_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {auth_token}"}
        print("   ✅ Login successful")
    else:
        print(f"   ❌ Login failed: {login_response.text}")
        
        # Try without trailing slash
        login_response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        print(f"   Login status (no slash): {login_response.status_code}")
        if login_response.status_code == 200:
            auth_token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {auth_token}"}
            print("   ✅ Login successful (no slash)")
        else:
            print(f"   ❌ Login failed (no slash): {login_response.text}")
            print("   Cannot proceed without authentication")
            exit(1)
            
except Exception as e:
    print(f"   ❌ Login request failed: {e}")
    exit(1)

# Step 3: Get projects to find one to upload to
print("\n3️⃣ Getting projects...")
try:
    projects_response = requests.get(f"{API_URL}/projects/", headers=headers, timeout=10)
    print(f"   Projects status: {projects_response.status_code}")
    
    if projects_response.status_code == 200:
        projects = projects_response.json()
        if projects:
            project_id = projects[0]["id"]
            project_title = projects[0]["title"]
            print(f"   ✅ Found project: {project_title} ({project_id})")
        else:
            print("   ⚠️  No projects found, will create one")
            # Create a test project
            create_response = requests.post(f"{API_URL}/projects/", 
                json={
                    "title": f"Test Upload Project {int(time.time())}",
                    "description": "Test project for upload",
                    "genre": "fiction"
                }, 
                headers=headers, 
                timeout=10
            )
            if create_response.status_code == 200:
                project_id = create_response.json()["id"]
                print(f"   ✅ Created test project: {project_id}")
            else:
                print(f"   ❌ Failed to create project: {create_response.text}")
                exit(1)
    else:
        print(f"   ❌ Failed to get projects: {projects_response.text}")
        exit(1)
        
except Exception as e:
    print(f"   ❌ Projects request failed: {e}")
    exit(1)

# Step 4: Try to upload a file - this should reproduce the 503 error
print(f"\n4️⃣ Attempting file upload to project {project_id}...")
try:
    # Create a small test file
    test_content = f"Test file content - {time.time()}"
    test_file = io.BytesIO(test_content.encode())
    test_file.name = f"test_upload_{int(time.time())}.txt"
    
    files = {"file": (test_file.name, test_file, "text/plain")}
    data = {"project_id": project_id}
    
    upload_response = requests.post(
        f"{API_URL}/source-materials/upload",
        headers=headers,
        files=files,
        data=data,
        timeout=30
    )
    
    print(f"   Upload status: {upload_response.status_code}")
    
    if upload_response.status_code == 503:
        print("   🎯 REPRODUCED THE 503 ERROR!")
        print(f"   Error message: {upload_response.text}")
        response_data = upload_response.json()
        if "File upload service is temporarily unavailable" in response_data.get("detail", ""):
            print("   ✅ This is the exact error the user reported!")
        else:
            print("   ❓ Different 503 error than expected")
            
    elif upload_response.status_code == 200:
        print("   ✅ Upload successful - the issue might be fixed!")
        upload_data = upload_response.json()
        print(f"   File ID: {upload_data.get('id')}")
        print(f"   Filename: {upload_data.get('name', upload_data.get('filename'))}")
        
    else:
        print(f"   ❌ Upload failed with status {upload_response.status_code}")
        print(f"   Response: {upload_response.text}")
        
except Exception as e:
    print(f"   ❌ Upload request failed: {e}")

print("\n" + "="*80)
print("🏁 Test completed!") 