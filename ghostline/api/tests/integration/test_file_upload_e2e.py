"""
End-to-end tests for file upload functionality.
Tests against live API - NO MOCKS.
"""
import io
import os
import time
import uuid

import pytest
import requests


class TestFileUploadE2E:
    """Test file upload functionality end-to-end against live API."""
    
    API_URL = os.getenv("API_URL", "https://api.dev.ghostline.ai/api/v1")
    
    @pytest.fixture(scope="class")
    def test_user(self):
        """Create and authenticate a test user."""
        timestamp = int(time.time())
        user_data = {
            "email": f"upload_test_{timestamp}@example.com",
            "password": "TestPass123!",
            "username": f"uploadtest_{timestamp}",
            "full_name": "Upload Test User"
        }
        
        # Register user
        register_response = requests.post(
            f"{self.API_URL}/auth/register",
            json=user_data
        )
        
        if register_response.status_code != 200:
            print(f"Registration failed: {register_response.text}")
        
        # Always login after registration
        login_response = requests.post(
            f"{self.API_URL}/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Failed to login test user: {login_response.text}")
        
        token = login_response.json()["access_token"]
        
        return {"email": user_data["email"], "token": token}
    
    @pytest.fixture(scope="class")
    def auth_headers(self, test_user):
        """Get authentication headers."""
        return {"Authorization": f"Bearer {test_user['token']}"}
    
    @pytest.fixture(scope="class") 
    def test_project(self, auth_headers):
        """Create a test project for uploads."""
        project_data = {
            "title": f"Upload Test Project {int(time.time())}",
            "genre": "fiction",
            "description": "Testing file uploads"
        }
        
        response = requests.post(
            f"{self.API_URL}/projects/",
            json=project_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to create project: {response.text}"
        return response.json()
    
    def test_upload_text_file(self, auth_headers, test_project):
        """Test uploading a text file"""
        # Create test file
        file_content = b"This is a test document for GhostLine.\nIt contains sample text for testing."
        file_data = io.BytesIO(file_content)
        
        files = {
            'file': ('test_document.txt', file_data, 'text/plain')
        }
        
        response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        
        print(f"\nUpload response: {response.status_code}")
        print(f"Response: {response.text}")
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        result = response.json()
        assert 'id' in result
        assert result['name'] == 'test_document.txt'
        assert result['type'] == 'txt'
        assert result['size'] == len(file_content)
        assert result['status'] == 'completed'
        
        return result['id']
    
    def test_upload_pdf_file(self, auth_headers, test_project):
        """Test uploading a PDF file"""
        # Create minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
217
%%EOF"""
        
        file_data = io.BytesIO(pdf_content)
        
        files = {
            'file': ('test_document.pdf', file_data, 'application/pdf')
        }
        
        response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"PDF upload failed: {response.text}"
        
        result = response.json()
        assert result['type'] == 'pdf'
        assert result['name'] == 'test_document.pdf'
    
    def test_duplicate_file_handling(self, auth_headers, test_project):
        """Test uploading the same file twice"""
        file_content = b"Duplicate test content"
        filename = f"duplicate_{int(time.time())}.txt"
        
        # First upload
        files1 = {
            'file': (filename, io.BytesIO(file_content), 'text/plain')
        }
        
        response1 = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files1,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Second upload (same filename)
        files2 = {
            'file': (filename, io.BytesIO(file_content), 'text/plain')
        }
        
        response2 = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files2,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        assert response2.status_code == 200
        
        result = response2.json()
        assert result.get('duplicate') == True
        assert 'already exists' in result.get('message', '')
    
    def test_invalid_file_type(self, auth_headers, test_project):
        """Test uploading unsupported file type"""
        files = {
            'file': ('test.exe', io.BytesIO(b"fake exe content"), 'application/x-executable')
        }
        
        response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert 'not allowed' in response.json()['detail']
    
    def test_file_too_large(self, auth_headers, test_project):
        """Test uploading file exceeding size limit"""
        # Create 51MB file (over 50MB limit)
        large_content = b"x" * (51 * 1024 * 1024)
        
        files = {
            'file': ('large_file.txt', io.BytesIO(large_content), 'text/plain')
        }
        
        response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert 'too large' in response.json()['detail']
    
    def test_upload_without_project(self, auth_headers):
        """Test that upload requires project_id"""
        files = {
            'file': ('test.txt', io.BytesIO(b"test"), 'text/plain')
        }
        
        response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code in [422, 400]  # Missing required parameter
    
    def test_full_upload_flow(self, auth_headers, test_project):
        """Test complete upload flow including retrieval"""
        # Upload file
        file_content = b"Full flow test content"
        filename = f"flow_test_{int(time.time())}.txt"
        files = {
            'file': (filename, io.BytesIO(file_content), 'text/plain')
        }
        
        upload_response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        assert upload_response.status_code == 200
        
        material_id = upload_response.json()['id']
        
        # Try to retrieve it
        get_response = requests.get(
            f"{self.API_URL}/source-materials/{material_id}",
            headers=auth_headers
        )
        
        print(f"\nGet material response: {get_response.status_code}")
        if get_response.status_code == 200:
            material = get_response.json()
            print(f"Material details: {material}")
            assert material['filename'] == filename
        
        # List materials for project
        list_response = requests.get(
            f"{self.API_URL}/projects/{test_project['id']}/source-materials",
            headers=auth_headers
        )
        
        print(f"\nList materials response: {list_response.status_code}")
        if list_response.status_code == 200:
            materials = list_response.json()
            print(f"Found {len(materials)} materials")
            # Check our file is in the list
            found = any(m['filename'] == filename for m in materials)
            assert found, f"Uploaded file {filename} not found in project materials"
    
    def test_upload_image_file(self, auth_headers, test_project):
        """Test uploading an image file"""
        # Create minimal valid JPG
        jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\xff\xd9'
        
        files = {
            'file': ('test_image.jpg', io.BytesIO(jpg_content), 'image/jpeg')
        }
        
        response = requests.post(
            f"{self.API_URL}/source-materials/upload",
            files=files,
            data={'project_id': test_project['id']},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Image upload failed: {response.text}"
        
        result = response.json()
        assert result['type'] in ['jpg', 'jpeg']
        assert result['name'] == 'test_image.jpg'
        assert result['status'] == 'completed'
    
    def test_concurrent_uploads(self, auth_headers, test_project):
        """Test multiple concurrent uploads"""
        import concurrent.futures
        
        def upload_file(index):
            """Upload a single file"""
            content = f"Concurrent test file {index}".encode()
            filename = f"concurrent_{index}_{int(time.time())}.txt"
            files = {
                'file': (filename, io.BytesIO(content), 'text/plain')
            }
            
            response = requests.post(
                f"{self.API_URL}/source-materials/upload",
                files=files,
                data={'project_id': test_project['id']},
                headers=auth_headers
            )
            
            return response.status_code == 200, filename
        
        # Upload 5 files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_file, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Check all uploads succeeded
        success_count = sum(1 for success, _ in results if success)
        assert success_count == 5, f"Only {success_count}/5 concurrent uploads succeeded"
        
        print(f"\n✅ All {success_count} concurrent uploads succeeded")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 