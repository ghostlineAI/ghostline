"""Test CORS configuration to prevent regression."""
import os

from fastapi.testclient import TestClient


def test_cors_headers_for_dev_frontend():
    """Test that CORS headers are properly set for dev.ghostline.ai."""
    # Import here to ensure fresh app instance
    from app.main import app

    client = TestClient(app)

    # Test OPTIONS preflight request
    response = client.options(
        "/health",
        headers={"Origin": "https://dev.ghostline.ai"}
    )

    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://dev.ghostline.ai"
    assert response.headers["access-control-allow-credentials"] == "true"

    # Test actual GET request with Origin header
    response = client.get(
        "/health",
        headers={"Origin": "https://dev.ghostline.ai"}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://dev.ghostline.ai"


def test_cors_headers_for_localhost():
    """Test that CORS headers work for localhost development."""
    from app.main import app

    client = TestClient(app)

    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )

    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_headers_for_cloudfront():
    """Test that CORS headers work for CloudFront."""
    from app.main import app

    client = TestClient(app)

    response = client.options(
        "/health",
        headers={"Origin": "https://d2thhts2eu7se8.cloudfront.net"}
    )

    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://d2thhts2eu7se8.cloudfront.net"


def test_cors_env_var_parsing():
    """Test that BACKEND_CORS_ORIGINS env var is parsed correctly."""
    # Test JSON array format
    os.environ["BACKEND_CORS_ORIGINS"] = '["https://example.com", "https://test.com"]'
    from app.core.config import Settings
    settings = Settings()
    assert settings.BACKEND_CORS_ORIGINS == ["https://example.com", "https://test.com"]

    # Test comma-separated format
    os.environ["BACKEND_CORS_ORIGINS"] = "https://example.com,https://test.com"
    settings = Settings()
    assert settings.BACKEND_CORS_ORIGINS == ["https://example.com", "https://test.com"]

    # Test single origin
    os.environ["BACKEND_CORS_ORIGINS"] = "https://example.com"
    settings = Settings()
    assert settings.BACKEND_CORS_ORIGINS == ["https://example.com"]

    # Test malformed JSON falls back gracefully
    # Missing closing bracket
    os.environ["BACKEND_CORS_ORIGINS"] = '["https://example.com"'
    settings = Settings()
    assert "https://example.com" in str(settings.BACKEND_CORS_ORIGINS)

    # Clean up
    if "BACKEND_CORS_ORIGINS" in os.environ:
        del os.environ["BACKEND_CORS_ORIGINS"]


def test_cors_blocks_unauthorized_origin():
    """Test that CORS blocks requests from unauthorized origins."""
    from app.main import app

    client = TestClient(app)

    response = client.options(
        "/health",
        headers={"Origin": "https://evil-site.com"}
    )

    # Should not have the evil origin in the response
    if "access-control-allow-origin" in response.headers:
        assert response.headers["access-control-allow-origin"] != "https://evil-site.com"
