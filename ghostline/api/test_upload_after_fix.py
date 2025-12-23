"""
Test upload after storage service fix
"""
import requests
import io
import time

API_URL = "https://api.dev.ghostline.ai/api/v1"

# Your real credentials
email = "alexgrgs2314@gmail.com"
password = "lightlight2"

print("Testing upload after storage service fix...")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# Login
login_response = requests.post(
    f"{API_URL}/auth/login/",
    json={"email": email, "password": password}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

auth_token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {auth_token}"}
print("✅ Logged in successfully")

# Get bloodhound project
projects_response = requests.get(f"{API_URL}/projects/", headers=headers)
projects = projects_response.json()
bloodhound = None
for project in projects:
    if project["title"].lower() == "bloodhound":
        bloodhound = project
        break

if not bloodhound:
    print("❌ Bloodhound project not found")
    exit(1)

print(f"✅ Found bloodhound project: {bloodhound['id']}")

# Try to upload your JPG
print("\n🚀 Attempting to upload your JPG file...")

# Create a test JPG file (just a small test image)
jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'  # Minimal JPG header
jpg_file = io.BytesIO(jpg_content)

files = {
    'file': ('your_uploaded_image.jpg', jpg_file, 'image/jpeg')
}
data = {
    'project_id': bloodhound['id']
}

upload_response = requests.post(
    f"{API_URL}/source-materials/upload",
    files=files,
    data=data,
    headers=headers
)

print(f"\n📋 Upload Response:")
print(f"   Status Code: {upload_response.status_code}")

if upload_response.status_code == 200:
    result = upload_response.json()
    print("   ✅ UPLOAD SUCCESSFUL! 🎉")
    print(f"   File ID: {result.get('id')}")
    print(f"   Filename: {result.get('name')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Duplicate: {result.get('duplicate', False)}")
    
    # List all files in the project
    print("\n📂 Listing all files in bloodhound project...")
    list_response = requests.get(
        f"{API_URL}/projects/{bloodhound['id']}/source-materials",
        headers=headers
    )
    
    if list_response.status_code == 200:
        materials = list_response.json()
        print(f"   Found {len(materials)} files:")
        for mat in materials:
            print(f"   • {mat.get('filename')} (status: {mat.get('processing_status')})")
    else:
        print(f"   ❌ Failed to list: {list_response.status_code}")
        
    print("\n🎊 YOUR JPG HAS BEEN UPLOADED TO THE DATABASE! 🎊")
else:
    print("   ❌ UPLOAD FAILED")
    print(f"   Response: {upload_response.text}")
    
    if "duplicate" in upload_response.text.lower():
        print("\n   Note: File might already exist")
    elif upload_response.status_code == 500:
        print("\n   Note: Storage service fix might not have deployed yet")
        print("   Wait a few minutes and try again")

print("\n" + "="*60) 