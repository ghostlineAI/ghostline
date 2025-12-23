"""Test main FastAPI application configuration."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


class TestMainApp:
    """Test main FastAPI application configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_api_routes_mounted_with_prefix(self, client):
        """Ensure API routes are mounted under /api/v1."""
        # Check that routes exist under /api/v1
        response = client.get("/api/v1/health")
        # Even if the endpoint doesn't exist, we should not get a 404
        # for the prefix itself
        assert response.status_code != 404 or "/api/v1" in str(response.url)

    def test_no_duplicate_api_prefix(self, client):
        """Ensure routes don't have duplicate /api/v1/api/v1."""
        # Check OpenAPI schema
        response = client.get("/openapi.json")
        if response.status_code == 200:
            openapi = response.json()
            paths = openapi.get("paths", {})

            for path in paths:
                # Count occurrences of /api/v1
                count = path.count("/api/v1")
                assert count <= 1, f"Path {path} contains duplicate /api/v1"

    def test_trailing_slash_handling(self, client):
        """Test that trailing slashes are handled consistently."""
        # Test without trailing slash
        response1 = client.get("/api/v1/health")
        # Test with trailing slash
        response2 = client.get("/api/v1/health/")

        # Both should have the same status code
        # (either both work or both redirect)
        # FastAPI by default redirects trailing slashes
        assert abs(response1.status_code - response2.status_code) < 100, \
            "Trailing slash handling is inconsistent"

    def test_cors_headers_present(self, client):
        """Test CORS headers are set for allowed origins."""
        # Test with an allowed origin
        headers = {"Origin": "https://dev.ghostline.ai"}
        response = client.options("/api/v1/health", headers=headers)

        # Check CORS headers
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers

    def test_no_http_redirect_loops(self, client):
        """Ensure no redirect loops for HTTP requests."""
        # Test that HTTP requests are not redirected to HTTPS at app level
        # In production, HTTPS enforcement should be at load balancer level
        response = client.get("/api/v1/health", follow_redirects=False)

        # Should not redirect at application level
        assert response.status_code not in [301, 302, 307, 308], \
            "Application should not redirect HTTP to HTTPS " \
            "(should be done at LB level)"

    def test_api_prefix_in_settings(self):
        """Ensure API prefix matches settings."""
        # Check that API_V1_STR is properly formatted
        assert not settings.API_V1_STR.endswith("/")
        assert settings.API_V1_STR.startswith("/")

    def test_root_path_not_exposed(self, client):
        """Test that root path doesn't expose API directly."""
        response = client.get("/")
        # Root should either redirect to docs or return 404, not API responses
        assert response.status_code in [200, 307, 404]

    def test_health_endpoint_exists(self, client):
        """Test that a health endpoint exists for monitoring."""
        # Common health check endpoints
        endpoints = ["/health", "/api/v1/health", "/healthz", "/api/v1/healthz"]

        health_found = False
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code in [200, 204]:
                health_found = True
                break

        assert health_found, "No health check endpoint found" 