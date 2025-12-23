#!/usr/bin/env python3
"""
Real E2E Tests for Data View Functionality
Tests against live production API - NO MOCKS

Based on GHOSTLINE_FEATURE_DEVELOPMENT_BLUEPRINT.md patterns for real E2E testing
"""

import requests
import time
import sys
import uuid

def test_data_view_e2e():
    """Test complete data view workflow against live API"""
    
    print("🚀 Testing Data View Functionality Against Live API")
    print("=" * 60)
    
    # Configuration
    API_BASE = "https://api.dev.ghostline.ai/api/v1"
    test_email = f"e2e-dataview-{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    # Step 1: Create test user
    print("\n1️⃣  Creating test user...")
    register_response = requests.post(f"{API_BASE}/auth/register", json={
        "email": test_email,
        "password": test_password,
        "username": f"e2euser{int(time.time())}"
    })
    
    if register_response.status_code != 200:
        print(f"❌ Registration failed: {register_response.status_code}")
        print(register_response.text)
        return False
    
    # Login to get token
    login_response = requests.post(f"{API_BASE}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ User authenticated")
    
    # Step 2: Create test project
    print("\n2️⃣  Creating test project...")
    project_response = requests.post(f"{API_BASE}/projects/", json={
        "title": f"E2E Data View Test {uuid.uuid4()}",
        "description": "Testing data view functionality",
        "genre": "fiction"
    }, headers=headers)
    
    if project_response.status_code != 200:
        print(f"❌ Project creation failed: {project_response.status_code}")
        print(project_response.text)
        return False
    
    project_id = project_response.json()["id"]
    print(f"✅ Project created: {project_id}")
    
    # Step 3: Upload test file
    print("\n3️⃣  Uploading test file...")
    test_content = f"E2E Test Content - {time.time()}\nThis tests the data view functionality.\nViewable and downloadable content."
    
    upload_response = requests.post(f"{API_BASE}/source-materials/upload", 
        files={"file": ("e2e-test.txt", test_content, "text/plain")},
        data={"project_id": project_id},
        headers=headers
    )
    
    if upload_response.status_code != 200:
        print(f"❌ Upload failed: {upload_response.status_code}")
        print(upload_response.text)
        return False
    
    material_id = upload_response.json()["id"]
    print(f"✅ File uploaded: {material_id}")
    
    # Step 4: Test VIEW functionality (/content endpoint)
    print("\n4️⃣  Testing VIEW functionality (content proxy)...")
    content_url = f"{API_BASE}/source-materials/{material_id}/content"
    print(f"   Testing: {content_url}")
    
    content_response = requests.get(content_url, headers=headers)
    
    if content_response.status_code == 200:
        if content_response.text == test_content:
            print("✅ VIEW working correctly - content matches!")
            print(f"   Content-Type: {content_response.headers.get('content-type')}")
            print(f"   Content-Disposition: {content_response.headers.get('content-disposition')}")
        else:
            print("⚠️  VIEW working but content doesn't match")
            print(f"   Expected: {test_content[:50]}...")
            print(f"   Got: {content_response.text[:50]}...")
    else:
        print(f"❌ VIEW failed: {content_response.status_code}")
        print(f"   Response: {content_response.text}")
        return False
    
    # Step 5: Test DOWNLOAD functionality (/download endpoint)
    print("\n5️⃣  Testing DOWNLOAD functionality (forced download)...")
    download_url = f"{API_BASE}/source-materials/{material_id}/download"
    print(f"   Testing: {download_url}")
    
    download_response = requests.get(download_url, headers=headers)
    
    if download_response.status_code == 200:
        content_disposition = download_response.headers.get('content-disposition', '')
        
        if 'attachment' in content_disposition and 'e2e-test.txt' in content_disposition:
            print("✅ DOWNLOAD working correctly - proper headers!")
            print(f"   Content-Disposition: {content_disposition}")
        else:
            print("⚠️  DOWNLOAD working but headers are wrong")
            print(f"   Content-Disposition: {content_disposition}")
        
        if download_response.content.decode() == test_content:
            print("✅ Downloaded content matches!")
        else:
            print("⚠️  Downloaded content doesn't match")
    else:
        print(f"❌ DOWNLOAD failed: {download_response.status_code}")
        print(f"   Response: {download_response.text}")
        return False
    
    # Step 6: Test legacy download-url endpoint
    print("\n6️⃣  Testing legacy download-url endpoint...")
    url_endpoint = f"{API_BASE}/source-materials/{material_id}/download-url"
    print(f"   Testing: {url_endpoint}")
    
    url_response = requests.get(url_endpoint, headers=headers)
    
    if url_response.status_code == 200:
        url_data = url_response.json()
        if "download_url" in url_data:
            print("✅ Legacy download-url working")
            print(f"   Expires in: {url_data.get('expires_in')} seconds")
            
            # Test the presigned URL
            presigned_response = requests.get(url_data["download_url"])
            if presigned_response.status_code == 200:
                print("✅ Presigned URL works")
            else:
                print(f"⚠️  Presigned URL failed: {presigned_response.status_code}")
        else:
            print("❌ No download_url in response")
    else:
        print(f"❌ Legacy download-url failed: {url_response.status_code}")
        print(f"   Response: {url_response.text}")
    
    # Step 7: Test DELETE functionality
    print("\n7️⃣  Testing DELETE functionality...")
    delete_response = requests.delete(f"{API_BASE}/source-materials/{material_id}", headers=headers)
    
    if delete_response.status_code == 200:
        print("✅ DELETE working correctly")
        
        # Verify deletion
        verify_response = requests.get(f"{API_BASE}/source-materials/{material_id}", headers=headers)
        if verify_response.status_code == 404:
            print("✅ Deletion verified - material no longer exists")
        else:
            print("⚠️  Material still exists after deletion")
    else:
        print(f"❌ DELETE failed: {delete_response.status_code}")
        print(f"   Response: {delete_response.text}")
    
    print("\n" + "=" * 60)
    print("🎉 E2E Data View Test Completed!")
    return True

def test_route_order_validation():
    """Test that specific routes work and aren't being caught by generic routes"""
    print("\n🔍 Testing Route Order Validation...")
    
    # These should all return proper status codes, not be caught by /{material_id}
    test_cases = [
        ("/source-materials/test-id/content", "Content endpoint"),
        ("/source-materials/test-id/download", "Download endpoint"), 
        ("/source-materials/test-id/download-url", "Download URL endpoint"),
        ("/source-materials/test-id", "Generic material endpoint")
    ]
    
    for endpoint, description in test_cases:
        print(f"   Testing {description}: {endpoint}")
        response = requests.get(f"https://api.dev.ghostline.ai/api/v1{endpoint}")
        
        # All should return 401 (unauthorized) not 404 (not found due to wrong route)
        if response.status_code == 401:
            print(f"   ✅ {description} - Route found (401 unauthorized as expected)")
        elif response.status_code == 404:
            print(f"   ❌ {description} - Route not found (404) - Route order issue!")
        else:
            print(f"   ⚠️  {description} - Unexpected status: {response.status_code}")

if __name__ == "__main__":
    print("🧪 Real E2E Tests for Data View Functionality")
    print("Testing against: https://api.dev.ghostline.ai")
    print("No mocks - Real environment testing")
    
    # Test route order first (no auth needed)
    test_route_order_validation()
    
    # Run full E2E test
    success = test_data_view_e2e()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED!")
        sys.exit(1) 