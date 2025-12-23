"""
FINAL TEST - Everything should work now!
"""
import requests
import io
import time

API_URL = "https://api.dev.ghostline.ai/api/v1"

# Your real credentials
email = "alexgrgs2314@gmail.com"
password = "lightlight2"

print("🚀 FINAL UPLOAD TEST - Everything is deployed!")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# Login
login_response = requests.post(
    f"{API_URL}/auth/login/",
    json={"email": email, "password": password}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    exit(1)

auth_token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {auth_token}"}
print("✅ Logged in successfully")

# Get bloodhound project
projects_response = requests.get(f"{API_URL}/projects/", headers=headers)
projects = projects_response.json()
bloodhound_project = next(
    (p for p in projects if p["title"] == "bloodhound"), 
    None
)

if not bloodhound_project:
    print("❌ No bloodhound project found")
    exit(1)

project_id = bloodhound_project["id"]
print(f"✅ Found bloodhound project: {project_id}")

# Create test JPG file
jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'
jpg_file = io.BytesIO(jpg_content)
jpg_file.name = f"bloodhound_test_{int(time.time())}.jpg"

# Upload JPG file
print(f"\n📤 Uploading: {jpg_file.name}")
files = {"file": (jpg_file.name, jpg_file, "image/jpeg")}
data = {"project_id": project_id}
upload_response = requests.post(
    f"{API_URL}/source-materials/upload",
    headers=headers,
    files=files,
    data=data
)

print(f"   Status: {upload_response.status_code}")

if upload_response.status_code == 200:
    print("\n🎉🎉🎉 SUCCESS! YOUR JPG IS UPLOADED! 🎉🎉🎉")
    upload_data = upload_response.json()
    print(f"\n📋 Upload Details:")
    print(f"   File ID: {upload_data.get('id')}")
    print(f"   Filename: {upload_data.get('filename')}")
    print(f"   S3 URL: {upload_data.get('s3_url')}")
    print(f"   Processing Status: {upload_data.get('processing_status')}")
    print(f"\n✅ THE FILE UPLOAD FEATURE IS FULLY WORKING!")
else:
    print(f"\n❌ Upload failed with status {upload_response.status_code}")
    print(f"   Response: {upload_response.text[:500]}")
    
print("\n" + "="*60) 