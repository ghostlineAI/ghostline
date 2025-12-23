#!/usr/bin/env python3
"""
Production test for data room feature.
Tests upload, list, view, and delete functionality.
"""

import requests
import json
import os
import time
from datetime import datetime

# Configuration
API_BASE_URL = "https://api.dev.ghostline.ai"
APP_BASE_URL = "https://dev.ghostline.ai"

def test_data_room_production():
    """Test the data room feature in production."""
    print("🧪 Testing Data Room Feature in Production")
    print("=" * 50)
    
    # Step 1: Create test user
    print("\n1. Creating test user...")
    timestamp = int(time.time())
    user_data = {
        "email": f"dataroom_test_{timestamp}@example.com",
        "password": "TestPass123!",
        "username": f"dataroomtest_{timestamp}",
        "full_name": "Data Room Test User"
    }
    
    # Register user
    register_response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json=user_data
    )
    
    if register_response.status_code != 200:
        print(f"⚠️ Registration failed: {register_response.status_code}")
        print("User might already exist, trying to login...")
    else:
        print("✅ User created successfully")
    
    # Step 2: Login
    print("\n2. Logging in...")
    login_response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Step 3: Create test project
    print("\n3. Creating test project...")
    project_data = {
        "title": f"Data Room Test Project {timestamp}",
        "genre": "fiction",
        "description": "Testing data room functionality"
    }
    
    project_response = requests.post(
        f"{API_BASE_URL}/api/v1/projects/",
        json=project_data,
        headers=headers
    )
    
    if project_response.status_code != 200:
        print(f"❌ Failed to create project: {project_response.status_code}")
        print(project_response.text)
        return False
    
    project = project_response.json()
    project_id = project["id"]
    print(f"✅ Created project: {project['title']} (ID: {project_id})")
    
    # Step 4: Create test file
    print("\n4. Creating test file...")
    test_filename = f"test_document_{int(time.time())}.txt"
    test_content = f"This is a test document uploaded at {datetime.now()}"
    
    # Step 5: Upload file
    print(f"\n5. Uploading {test_filename}...")
    files = {"file": (test_filename, test_content, "text/plain")}
    data = {"project_id": project_id}
    
    upload_response = requests.post(
        f"{API_BASE_URL}/api/v1/source-materials/upload",
        files=files,
        data=data,
        headers=headers
    )
    
    if upload_response.status_code != 200:
        print(f"❌ Upload failed: {upload_response.status_code}")
        print(upload_response.text)
        return False
    
    upload_data = upload_response.json()
    material_id = upload_data["id"]
    print(f"✅ File uploaded successfully (ID: {material_id})")
    
    # Step 6: List materials
    print("\n6. Listing materials...")
    list_response = requests.get(
        f"{API_BASE_URL}/api/v1/projects/{project_id}/source-materials",
        headers=headers
    )
    
    if list_response.status_code != 200:
        print(f"❌ Failed to list materials: {list_response.status_code}")
        return False
    
    materials = list_response.json()
    found = any(m["id"] == material_id for m in materials)
    if not found:
        print(f"❌ Uploaded file not found in list")
        return False
    
    print(f"✅ Found {len(materials)} materials, including our upload")
    
    # Step 7: Get specific material (VIEW functionality)
    print("\n7. Testing VIEW functionality...")
    get_response = requests.get(
        f"{API_BASE_URL}/api/v1/source-materials/{material_id}",
        headers=headers
    )
    
    if get_response.status_code != 200:
        print(f"❌ Failed to get material: {get_response.status_code}")
        return False
    
    material = get_response.json()
    print(f"✅ Material details: {material['filename']}, {material['file_size']} bytes")
    
    # Step 8: Test download functionality
    print("\n8. Testing DOWNLOAD functionality...")
    download_response = requests.get(
        f"{API_BASE_URL}/api/v1/source-materials/{material_id}/download",
        headers=headers
    )
    
    if download_response.status_code != 200:
        print(f"❌ Failed to get download URL: {download_response.status_code}")
        print(download_response.text)
        return False
    
    download_data = download_response.json()
    if "download_url" not in download_data:
        print("❌ Download URL not found in response")
        return False
    
    download_url = download_data["download_url"]
    print(f"✅ Download URL generated: {download_url[:100]}...")
    
    # Actually test the download URL by downloading the file
    print("   Testing actual file download...")
    try:
        file_download_response = requests.get(download_url, timeout=30)
        
        if file_download_response.status_code != 200:
            print(f"❌ Download failed: {file_download_response.status_code}")
            print(f"   Error: {file_download_response.text[:200]}")
            return False
        
        downloaded_content = file_download_response.content.decode('utf-8')
        if test_content in downloaded_content:
            print("✅ File downloaded successfully and content matches!")
        else:
            print(f"❌ Downloaded content doesn't match original")
            print(f"   Expected: {test_content}")
            print(f"   Got: {downloaded_content}")
            return False
            
    except Exception as e:
        print(f"❌ Download request failed: {e}")
        return False
    
    # Step 9: Delete material
    print("\n9. Testing DELETE functionality...")
    delete_response = requests.delete(
        f"{API_BASE_URL}/api/v1/source-materials/{material_id}",
        headers=headers
    )
    
    if delete_response.status_code != 200:
        print(f"❌ Failed to delete material: {delete_response.status_code}")
        print(f"Error response: {delete_response.text}")
        return False
    
    print("✅ Material deleted successfully")
    
    # Step 10: Verify deletion
    print("\n10. Verifying deletion...")
    verify_response = requests.get(
        f"{API_BASE_URL}/api/v1/source-materials/{material_id}",
        headers=headers
    )
    
    if verify_response.status_code != 404:
        print(f"❌ Material still exists after deletion")
        return False
    
    print("✅ Deletion confirmed")
    
    # Step 11: UI Test Instructions
    print(f"\n11. UI Test Instructions:")
    print(f"   1. Go to {APP_BASE_URL}/dashboard/data-room")
    print(f"   2. Select a project")
    print(f"   3. Upload a file")
    print(f"   4. Verify the file appears in the list below")
    print(f"   5. Click the eye icon to preview (for supported types)")
    print(f"   6. Click the trash icon to delete")
    print(f"   7. Confirm deletion in the dialog")
    
    print("\n✅ All API tests passed!")
    return True


if __name__ == "__main__":
    try:
        success = test_data_room_production()
        if success:
            print("\n🎉 Data Room feature is working correctly in production!")
        else:
            print("\n❌ Some tests failed. Please check the errors above.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 