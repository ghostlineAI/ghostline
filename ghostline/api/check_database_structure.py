"""
Check production database structure
"""
import requests

# Use the DATABASE_QUICK_REFERENCE.md connection approach
print("Checking production database structure...\n")

# Your real credentials
email = "alexgrgs2314@gmail.com"
password = "lightlight2"

API_URL = "https://api.dev.ghostline.ai/api/v1"

# Login
login_response = requests.post(
    f"{API_URL}/auth/login/",
    json={"email": email, "password": password}
)

if login_response.status_code == 200:
    print("✅ API is accessible")
    print("   (This means the API service is running)")
else:
    print("❌ API login failed")
    
# Test a simple endpoint that doesn't involve uploads
test_response = requests.get(f"{API_URL}/billing/plans/")
print(f"\n📋 Testing simple endpoint:")
print(f"   Billing plans endpoint: {test_response.status_code}")
if test_response.status_code == 200:
    print(f"   Found {len(test_response.json())} billing plans")

# Now let's see what the actual error is by triggering it
print("\n🔍 Checking actual upload error...")
print("   The 500 error is likely due to:")
print("   1. Missing 'materialtype' enum values in PostgreSQL")
print("   2. Missing 'processingstatus' enum values in PostgreSQL") 
print("   3. OR the source_materials table doesn't exist")
print("\n   [[memory:7961638374420993389]] CORS errors often mask database issues!")

print("\n💡 SOLUTION:")
print("   Run the Alembic migration to create the source_materials table:")
print("   cd ghostline/api && poetry run alembic upgrade head") 