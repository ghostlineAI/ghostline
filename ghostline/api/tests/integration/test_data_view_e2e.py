"""
E2E Tests for Data View Functionality (VIEW UPLOADED MATERIALS)

This test validates the complete data view workflow:
1. Upload files
2. List materials
3. VIEW: Get content via proxy endpoint (no CORS)
4. DOWNLOAD: Force download with proper headers
5. DELETE: Remove materials

DO NOT USE MOCKS - These are live integration tests.
"""

import io
import os
import uuid
from datetime import datetime

import pytest
import requests
from PIL import Image
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.source_material import SourceMaterial
from app.models.user import User


class TestDataViewE2E:
    """End-to-end tests for data view functionality."""

    def test_complete_data_view_workflow(
        self, client, db: Session, auth_headers: dict, test_user: User
    ):
        """Test the complete data view workflow: upload, view, download, delete."""
        
        print("\n[E2E] Starting complete data view workflow test")
        
        # Step 1: Create a test project
        project_data = {
            "title": f"Data View Test Project {uuid.uuid4()}",
            "description": "Test project for data view E2E test",
            "genre": "fiction"
        }
        
        response = client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        project = response.json()
        project_id = project["id"]
        
        print(f"[E2E] Created test project: {project_id}")

        # Step 2: Upload test files
        test_files = [
            ("test.txt", b"This is test content for viewing", "text/plain"),
            ("test.jpg", self._create_test_image(), "image/jpeg"),
            ("test.mp3", b"Fake MP3 audio data", "audio/mpeg"),
        ]
        
        uploaded_materials = []
        for filename, content, content_type in test_files:
            print(f"\n[E2E] Uploading: {filename}")
            
            response = client.post(
                "/api/v1/source-materials/upload",
                files={"file": (filename, content, content_type)},
                data={"project_id": project_id},
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            result = response.json()
            uploaded_materials.append({
                "id": result["id"],
                "filename": filename,
                "content": content,
                "content_type": content_type
            })
            print(f"[E2E] ✅ Uploaded: {filename} -> {result['id']}")

        # Step 3: Test VIEW functionality (content proxy endpoint)
        print("\n[E2E] Testing VIEW functionality (content proxy)")
        
        for material in uploaded_materials:
            material_id = material["id"]
            filename = material["filename"]
            
            print(f"\n[E2E] Testing content view for: {filename}")
            
            # Get content via proxy endpoint (avoids CORS)
            response = client.get(
                f"/api/v1/source-materials/{material_id}/content",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            content_type = response.headers.get("content-type") or ""
            assert content_type.startswith(material["content_type"])
            assert len(response.content) > 0
            
            # Verify content matches for text files
            if filename.endswith('.txt'):
                assert response.content == material["content"]
                print(f"[E2E] ✅ Text content matches for: {filename}")
            else:
                print(f"[E2E] ✅ Binary content received for: {filename}")

        # Step 4: Test DOWNLOAD functionality (forced download)
        print("\n[E2E] Testing DOWNLOAD functionality")
        
        for material in uploaded_materials:
            material_id = material["id"]
            filename = material["filename"]
            
            print(f"\n[E2E] Testing download for: {filename}")
            
            # Test download endpoint
            response = client.get(
                f"/api/v1/source-materials/{material_id}/download",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            
            # Verify download headers
            content_disposition = response.headers.get("content-disposition")
            assert content_disposition is not None
            assert "attachment" in content_disposition
            assert filename in content_disposition
            print(f"[E2E] ✅ Download headers correct for: {filename}")
            
            # Verify content
            assert len(response.content) > 0
            if filename.endswith('.txt'):
                assert response.content == material["content"]

        # Step 5: Test download URL endpoint (legacy)
        print("\n[E2E] Testing download URL generation")
        
        material_id = uploaded_materials[0]["id"]
        response = client.get(
            f"/api/v1/source-materials/{material_id}/download-url",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert "filename" in data
        assert "expires_in" in data
        assert data["expires_in"] == 3600
        print("[E2E] ✅ Download URL generation working")

        # Step 6: Test DELETE functionality
        print("\n[E2E] Testing DELETE functionality")
        
        for material in uploaded_materials:
            material_id = material["id"]
            filename = material["filename"]
            
            print(f"\n[E2E] Deleting: {filename}")
            
            response = client.delete(
                f"/api/v1/source-materials/{material_id}",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            
            # Verify deletion
            response = client.get(
                f"/api/v1/source-materials/{material_id}",
                headers=auth_headers,
            )
            assert response.status_code == 404
            print(f"[E2E] ✅ Deleted and verified: {filename}")

        print("\n[E2E] ✅ Complete data view workflow test PASSED")

    def test_cors_prevention_via_proxy(
        self, client, db: Session, auth_headers: dict, test_user: User
    ):
        """Test that content proxy prevents CORS issues."""
        
        print("\n[E2E] Testing CORS prevention via content proxy")
        
        # Create project and upload file
        project_data = {
            "title": f"CORS Test Project {uuid.uuid4()}",
            "description": "Test CORS prevention",
            "genre": "fiction"
        }
        
        response = client.post(
            "/api/v1/projects/",
            json=project_data,
            headers=auth_headers,
        )
        project_id = response.json()["id"]
        
        # Upload test file
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("cors-test.txt", b"CORS test content", "text/plain")},
            data={"project_id": project_id},
            headers=auth_headers,
        )
        material_id = response.json()["id"]
        
        # Test content endpoint returns proper headers
        response = client.get(
            f"/api/v1/source-materials/{material_id}/content",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        # Content endpoint should not have CORS restrictions since it's same-origin
        assert response.headers.get("cache-control") == "private, max-age=3600"
        print("[E2E] ✅ Content proxy working without CORS issues")

    def test_auth_protection(self, client, db: Session):
        """Test that all endpoints require authentication."""
        
        print("\n[E2E] Testing authentication protection")
        
        fake_id = str(uuid.uuid4())
        endpoints = [
            ("GET", f"/api/v1/source-materials/{fake_id}"),
            ("GET", f"/api/v1/source-materials/{fake_id}/content"),
            ("GET", f"/api/v1/source-materials/{fake_id}/download"),
            ("GET", f"/api/v1/source-materials/{fake_id}/download-url"),
            ("DELETE", f"/api/v1/source-materials/{fake_id}"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.delete(endpoint)
            
            assert response.status_code == 401
            print(f"[E2E] ✅ {method} {endpoint} requires auth")

    def _create_test_image(self):
        """Create a minimal test image."""
        img = Image.new('RGB', (10, 10), color='blue')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        return img_buffer.getvalue()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 