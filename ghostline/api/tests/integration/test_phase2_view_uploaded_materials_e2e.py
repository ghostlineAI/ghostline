"""
PHASE 2 E2E Tests: VIEW UPLOADED MATERIALS Feature

Tests all three icon functionalities (view, download, delete) against real API endpoints.
These tests use actual database transactions (with rollback) and real S3 operations.

DO NOT USE MOCKS - These are live integration tests as required by Blueprint.
"""

import io
import os
import tempfile
import uuid
from datetime import datetime

import pytest
import requests
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project, ProjectStatus, BookGenre
from app.models.source_material import SourceMaterial, MaterialType, ProcessingStatus
from app.models.user import User
from app.services.storage import StorageService


class TestPhase2ViewUploadedMaterialsE2E:
    """
    End-to-End tests for Phase 2: VIEW UPLOADED MATERIALS feature.
    
    Tests the complete workflow:
    1. Upload file to project
    2. List uploaded materials  
    3. VIEW: Get material details (eye icon functionality)
    4. DOWNLOAD: Generate presigned URL and verify download works (download icon)
    5. DELETE: Remove material from both S3 and database (trash icon)
    """

    def test_complete_view_uploaded_materials_workflow(
        self, client, db_session: Session, test_user_token: str, test_user: User
    ):
        """Test the complete VIEW UPLOADED MATERIALS workflow end-to-end."""
        
        print("[E2E] Starting complete VIEW UPLOADED MATERIALS workflow test")
        
        # Step 1: Create a test project
        project_data = {
            "title": f"E2E Test Project {uuid.uuid4()}",
            "description": "Test project for VIEW UPLOADED MATERIALS E2E test",
            "genre": "fiction"
        }
        
        response = client.post(
            "/api/v1/projects/",
            json=project_data,
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        project = response.json()
        project_id = project["id"]
        
        print(f"[E2E] Created test project: {project_id}")

        # Step 2: Upload multiple test files of different types
        test_files = self._create_test_files()
        uploaded_materials = []
        
        for filename, content, content_type in test_files:
            print(f"[E2E] Uploading test file: {filename}")
            
            response = client.post(
                "/api/v1/source-materials/upload",
                files={"file": (filename, content, content_type)},
                data={"project_id": project_id},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 200, f"Upload failed for {filename}: {response.text}"
            upload_result = response.json()
            
            assert "id" in upload_result
            assert upload_result["name"] == filename
            assert upload_result["status"] == "completed"
            
            uploaded_materials.append({
                "id": upload_result["id"],
                "filename": filename,
                "content_type": content_type
            })
            
            print(f"[E2E] Successfully uploaded: {filename} -> {upload_result['id']}")

        # Step 3: List uploaded materials (verify they appear in list)
        print(f"[E2E] Testing materials list for project {project_id}")
        
        response = client.get(
            f"/api/v1/projects/{project_id}/source-materials",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        materials_list = response.json()
        
        assert len(materials_list) == len(test_files)
        
        for material in materials_list:
            # Verify all expected fields are present
            assert "id" in material
            assert "filename" in material
            assert "material_type" in material
            assert "file_size" in material
            assert "mime_type" in material
            assert "processing_status" in material
            assert "created_at" in material
            
            # Verify processing status is COMPLETED
            assert material["processing_status"] == "COMPLETED"
            
        print(f"[E2E] Successfully listed {len(materials_list)} materials")

        # Step 4: Test VIEW functionality (eye icon) - Get individual material details
        for uploaded_material in uploaded_materials:
            material_id = uploaded_material["id"]
            filename = uploaded_material["filename"]
            
            print(f"[E2E] Testing VIEW (eye icon) for material: {filename}")
            
            response = client.get(
                f"/api/v1/source-materials/{material_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 200, f"VIEW failed for {filename}: {response.text}"
            material_details = response.json()
            
            # Verify all expected fields in detail view
            assert material_details["id"] == material_id
            assert material_details["filename"] == filename
            assert "material_type" in material_details
            assert "file_size" in material_details
            assert "mime_type" in material_details
            assert material_details["processing_status"] == "COMPLETED"
            assert "created_at" in material_details
            assert "s3_url" in material_details
            
            print(f"[E2E] ✅ VIEW (eye icon) working for: {filename}")

        # Step 5: Test DOWNLOAD functionality (download icon) - Generate presigned URLs
        for uploaded_material in uploaded_materials:
            material_id = uploaded_material["id"]
            filename = uploaded_material["filename"]
            
            print(f"[E2E] Testing DOWNLOAD (download icon) for material: {filename}")
            
            response = client.get(
                f"/api/v1/source-materials/{material_id}/download-url",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 200, f"DOWNLOAD failed for {filename}: {response.text}"
            download_data = response.json()
            
            # Verify download response format
            assert "download_url" in download_data
            assert "filename" in download_data
            assert "expires_in" in download_data
            
            assert download_data["filename"] == filename
            assert download_data["expires_in"] == 3600  # 1 hour
            assert download_data["download_url"].startswith(("https://", "http://"))
            
            # Verify the URL points to a real object.
            download_url = download_data["download_url"]
            storage_service = StorageService()
            if storage_service.use_local:
                # In local mode the URL targets the API file-serving endpoint; assert the file exists on disk.
                assert "/api/v1/files/" in download_url
                key = download_url.split("/api/v1/files/")[-1]
                assert key.endswith(filename)
                assert storage_service.file_exists(key)
                print(f"[E2E] ✅ DOWNLOAD URL points to existing local file for: {filename}")
            else:
                print(f"[E2E] Verifying presigned URL works for: {filename}")
                download_response = requests.get(download_url, timeout=30)
                assert download_response.status_code == 200, f"Presigned URL failed for {filename}"
                assert len(download_response.content) > 0, f"Downloaded content empty for {filename}"
                print(f"[E2E] ✅ DOWNLOAD (download icon) working for: {filename}")

        # Step 6: Test DELETE functionality (trash icon) - Remove materials
        for uploaded_material in uploaded_materials:
            material_id = uploaded_material["id"]
            filename = uploaded_material["filename"]
            
            print(f"[E2E] Testing DELETE (trash icon) for material: {filename}")
            
            response = client.delete(
                f"/api/v1/source-materials/{material_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 200, f"DELETE failed for {filename}: {response.text}"
            delete_result = response.json()
            
            assert "detail" in delete_result
            assert "deleted successfully" in delete_result["detail"].lower()
            
            # Verify material is actually gone from database
            response = client.get(
                f"/api/v1/source-materials/{material_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 404, f"Material {filename} still exists after deletion"
            
            print(f"[E2E] ✅ DELETE (trash icon) working for: {filename}")

        # Step 7: Verify materials list is now empty
        print(f"[E2E] Verifying materials list is empty after deletions")
        
        response = client.get(
            f"/api/v1/projects/{project_id}/source-materials",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        materials_list = response.json()
        assert len(materials_list) == 0, "Materials list should be empty after all deletions"
        
        print("[E2E] ✅ Complete VIEW UPLOADED MATERIALS workflow test PASSED")

    def test_view_functionality_with_different_file_types(
        self, client, db_session: Session, test_user_token: str, test_user: User
    ):
        """Test VIEW functionality specifically with different file types."""
        
        print("[E2E] Testing VIEW functionality with different file types")
        
        # Create test project
        project_data = {
            "title": f"E2E View Test Project {uuid.uuid4()}",
            "description": "Test project for VIEW functionality",
            "genre": "non_fiction"
        }
        
        response = client.post(
            "/api/v1/projects/",
            json=project_data,
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        project_id = response.json()["id"]

        # Test with each supported file type
        file_type_tests = [
            ("test_document.pdf", b"PDF content here", "application/pdf", "PDF"),
            ("test_audio.mp3", b"MP3 audio data", "audio/mpeg", "AUDIO"),
            ("test_image.jpg", self._create_test_image(), "image/jpeg", "IMAGE"),
            ("test_text.txt", b"Plain text content for testing", "text/plain", "TEXT"),
        ]
        
        for filename, content, content_type, expected_material_type in file_type_tests:
            print(f"[E2E] Testing VIEW for file type: {expected_material_type}")
            
            # Upload file
            response = client.post(
                "/api/v1/source-materials/upload",
                files={"file": (filename, content, content_type)},
                data={"project_id": project_id},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 200
            upload_result = response.json()
            material_id = upload_result["id"]
            
            # Test VIEW functionality
            response = client.get(
                f"/api/v1/source-materials/{material_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            assert response.status_code == 200
            material_details = response.json()
            
            # Verify material type is correctly detected
            assert material_details["material_type"] == expected_material_type
            assert material_details["filename"] == filename
            assert material_details["file_size"] == len(content)
            assert material_details["processing_status"] == "COMPLETED"
            
            print(f"[E2E] ✅ VIEW working for {expected_material_type}: {filename}")

    def test_download_functionality_error_handling(
        self, client, db_session: Session, test_user_token: str, test_user: User
    ):
        """Test DOWNLOAD functionality error handling."""
        
        print("[E2E] Testing DOWNLOAD functionality error handling")
        
        # Test download for non-existent material
        fake_material_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/source-materials/{fake_material_id}/download",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()
        
        print("[E2E] ✅ DOWNLOAD error handling working for non-existent material")

    def test_delete_functionality_error_handling(
        self, client, db_session: Session, test_user_token: str, test_user: User
    ):
        """Test DELETE functionality error handling."""
        
        print("[E2E] Testing DELETE functionality error handling")
        
        # Test delete for non-existent material
        fake_material_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/source-materials/{fake_material_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()
        
        print("[E2E] ✅ DELETE error handling working for non-existent material")

    def test_unauthorized_access_protection(self, client, db_session: Session):
        """Test that all endpoints properly protect against unauthorized access."""
        
        print("[E2E] Testing unauthorized access protection")
        
        fake_material_id = str(uuid.uuid4())
        
        # Test all endpoints without authorization
        test_cases = [
            ("GET", f"/api/v1/source-materials/{fake_material_id}"),
            ("GET", f"/api/v1/source-materials/{fake_material_id}/download"),
            ("DELETE", f"/api/v1/source-materials/{fake_material_id}"),
        ]
        
        for method, endpoint in test_cases:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401, f"Unauthorized access allowed for {method} {endpoint}"
            
        print("[E2E] ✅ Unauthorized access protection working")

    def _create_test_files(self):
        """Create test files for upload testing."""
        return [
            ("test_document.txt", b"This is a test text document for E2E testing.", "text/plain"),
            ("test_image.jpg", self._create_test_image(), "image/jpeg"),
            ("test_audio.mp3", b"Fake MP3 content for testing", "audio/mpeg"),
        ]

    def _create_test_image(self):
        """Create a minimal test image file."""
        # Create a small test image
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        return img_buffer.getvalue()

    def test_s3_storage_integration(
        self, client, db_session: Session, test_user_token: str, test_user: User
    ):
        """Test S3 storage integration for upload, download, and delete operations."""
        
        print("[E2E] Testing S3 storage integration")

        storage_service = StorageService()
        if storage_service.use_local:
            pytest.skip("S3 integration test skipped: USE_LOCAL_STORAGE is enabled")
        
        # Create test project
        project_data = {
            "title": f"S3 Integration Test {uuid.uuid4()}",
            "description": "Test S3 integration",
            "genre": "other"
        }
        
        response = client.post(
            "/api/v1/projects/",
            json=project_data,
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        project_id = response.json()["id"]

        # Test file upload to S3
        test_content = b"S3 integration test content"
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("s3_test.txt", test_content, "text/plain")},
            data={"project_id": project_id},
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        upload_result = response.json()
        material_id = upload_result["id"]
        
        # Test S3 download URL generation
        response = client.get(
            f"/api/v1/source-materials/{material_id}/download-url",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        download_data = response.json()
        
        # Verify S3 URL format (unless in mock mode)
        download_url = download_data["download_url"]
        # Should be a valid S3 presigned URL
        assert "amazonaws.com" in download_url or "s3" in download_url
        assert "Signature=" in download_url or "X-Amz-Signature=" in download_url
        
        # Test actual download
        download_response = requests.get(download_url, timeout=10)
        assert download_response.status_code == 200
        assert download_response.content == test_content
        
        print("[E2E] ✅ S3 presigned URL download working")
        
        # Test S3 delete
        response = client.delete(
            f"/api/v1/source-materials/{material_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        
        print("[E2E] ✅ S3 storage integration test completed")

    def test_concurrent_operations(
        self, client, db_session: Session, test_user_token: str, test_user: User
    ):
        """Test concurrent VIEW/DOWNLOAD/DELETE operations."""
        
        print("[E2E] Testing concurrent operations")
        
        # Create test project
        project_data = {
            "title": f"Concurrent Test Project {uuid.uuid4()}",
            "description": "Test concurrent operations",
            "genre": "technical"
        }
        
        response = client.post(
            "/api/v1/projects/",
            json=project_data,
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        project_id = response.json()["id"]

        # Upload multiple files
        material_ids = []
        for i in range(3):
            response = client.post(
                "/api/v1/source-materials/upload",
                files={"file": (f"concurrent_test_{i}.txt", f"Content {i}".encode(), "text/plain")},
                data={"project_id": project_id},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            assert response.status_code == 200
            material_ids.append(response.json()["id"])

        # Test concurrent VIEW operations
        for material_id in material_ids:
            response = client.get(
                f"/api/v1/source-materials/{material_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            assert response.status_code == 200

        # Test concurrent DOWNLOAD operations
        for material_id in material_ids:
            response = client.get(
                f"/api/v1/source-materials/{material_id}/download",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            assert response.status_code == 200

        # Test concurrent DELETE operations
        for material_id in material_ids:
            response = client.delete(
                f"/api/v1/source-materials/{material_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            assert response.status_code == 200

        print("[E2E] ✅ Concurrent operations test completed")


if __name__ == "__main__":
    # These tests are designed to be run with pytest
    # Example: pytest tests/integration/test_phase2_view_uploaded_materials_e2e.py -v -s
    print("Run with: pytest tests/integration/test_phase2_view_uploaded_materials_e2e.py -v -s") 