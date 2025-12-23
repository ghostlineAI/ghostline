#!/usr/bin/env python3
"""
Test upload against production with correct trailing slash endpoints
"""
import requests
import io
import time

API_URL = "https://api.dev.ghostline.ai/api/v1"

# Test credentials
email = "alexgrgs2314@gmail.com"
password = "lightlight2"

print("🧪 Testing Production Upload with Correct Endpoints")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Step 1: Login with trailing slash
print("\n1️⃣ Attempting login with trailing slash...")
try:
    login_response = requests.post(
        f"{API_URL}/auth/login/",  # Note trailing slash
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
        exit(1)
except Exception as e:
    print(f"   ❌ Login request failed: {e}")
    exit(1)

# Step 2: Get projects with trailing slash
print("\n2️⃣ Getting projects with trailing slash...")
try:
    projects_response = requests.get(f"{API_URL}/projects/", headers=headers, timeout=10)  # Note trailing slash
    print(f"   Projects status: {projects_response.status_code}")
    
    if projects_response.status_code == 200:
        projects = projects_response.json()
        if projects:
            project_id = projects[0]["id"]
            project_title = projects[0]["title"]
            print(f"   ✅ Found project: {project_title} ({project_id})")
        else:
            print("   ⚠️  No projects found")
            exit(1)
    else:
        print(f"   ❌ Failed to get projects: {projects_response.text}")
        exit(1)
except Exception as e:
    print(f"   ❌ Projects request failed: {e}")
    exit(1)

# Step 3: Test file upload (this is where the 503 error happens)
print(f"\n3️⃣ Testing file upload to project {project_id}...")
try:
    # Create a small test file
    test_content = f"Test file upload - {time.time()}"
    test_file = io.BytesIO(test_content.encode())
    test_file.name = f"production_upload_test_{int(time.time())}.txt"
    
    files = {"file": (test_file.name, test_file, "text/plain")}
    data = {"project_id": project_id}
    
    upload_response = requests.post(
        f"{API_URL}/source-materials/upload",  # Check if this needs trailing slash
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
            print("   ✅ This confirms the S3 StorageService is still in mock mode")
            print("   🔍 The issue is NOT with trailing slashes - it's still the S3 config")
        else:
            print("   ❓ Different 503 error than expected")
            
    elif upload_response.status_code == 200:
        print("   🎉 UPLOAD SUCCESSFUL!")
        upload_data = upload_response.json()
        print(f"   File ID: {upload_data.get('id')}")
        print(f"   Filename: {upload_data.get('name', upload_data.get('filename'))}")
        print("   ✅ S3 upload functionality is working!")
        
    else:
        print(f"   ❌ Upload failed with status {upload_response.status_code}")
        print(f"   Response: {upload_response.text}")
        
except Exception as e:
    print(f"   ❌ Upload request failed: {e}")

print("\n" + "="*80)
print("🏁 Production upload test completed!")
print("\nIf we see the 503 error, the issue is confirmed:")
print("- The StorageService is still falling back to mock mode")  
print("- Either the deployment didn't complete or the S3 config fix didn't work")
print("- Need to check ECS container logs to see the actual S3 initialization error") 