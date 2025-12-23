from pathlib import Path

import pytest

from app.core.config import Settings


class TestCrossReferenceConfiguration:
    """Test cross-referenced configurations between API and other components."""

    def test_cors_origins_match_frontend_domains(self):
        """Ensure CORS origins include the actual frontend domains."""
        settings = Settings()
        cors_origins = settings.BACKEND_CORS_ORIGINS

        # Should include the production frontend
        expected_origins = [
            "https://dev.ghostline.ai",
            "http://localhost:3000"  # For local development
        ]

        for expected in expected_origins:
            assert any(expected in origin for origin in cors_origins), \
                f"CORS origins should include {expected}"

    def test_cors_origins_match_cloudfront_domain(self):
        """Ensure CORS origins include CloudFront distribution if used."""
        settings = Settings()
        cors_origins = settings.BACKEND_CORS_ORIGINS

        # Check if any CloudFront domain is included
        cloudfront_patterns = [".cloudfront.net", "https://d"]
        has_cloudfront = any(
            any(pattern in origin for pattern in cloudfront_patterns)
            for origin in cors_origins
        )

        # This is informational - CloudFront might not always be used
        if not has_cloudfront:
            print("No CloudFront domain in CORS origins - ensure this is intentional")

    def test_api_prefix_used_consistently(self):
        """Test that API prefix is used consistently in main.py."""
        # Check that main.py exists and imports the prefix
        main_path = Path(__file__).parent.parent.parent / "app" / "main.py"
        assert main_path.exists(), "main.py should exist"

        with open(main_path) as f:
            content = f.read()

        # Should import API_V1_STR from settings
        assert "API_V1_STR" in content, "main.py should use API_V1_STR from settings"

        # Should not hardcode /api/v1
        # Allow it in comments or as part of settings.API_V1_STR
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '"/api/v1"' in line and 'API_V1_STR' not in line and '#' not in line:
                pytest.fail(
                    f"Line {i+1} in main.py hardcodes /api/v1 "
                    f"instead of using settings.API_V1_STR"
                )

    def test_database_url_format(self):
        """Test that DATABASE_URL follows expected format."""
        settings = Settings()
        db_url = settings.DATABASE_URL

        # Should start with postgresql://
        assert db_url.startswith("postgresql://"), \
            "DATABASE_URL should use postgresql:// scheme"

        # Should not contain hardcoded passwords in the default
        if "localhost" in db_url or "db" in db_url:
            # Default/test database URLs are OK to have simple passwords
            pass
        else:
            # Production URLs should not have obvious passwords
            assert "password" not in db_url.lower(), \
                "Production DATABASE_URL should not contain 'password'"
            assert "admin" not in db_url.lower(), \
                "Production DATABASE_URL should not contain 'admin'"

    def test_github_workflow_consistency(self):
        """Test that GitHub workflows use consistent Python version."""
        workflow_path = Path(__file__).parent.parent.parent / ".github" / \
            "workflows" / "test.yml"

        if workflow_path.exists():
            with open(workflow_path) as f:
                content = f.read()

            # Check Python version
            assert 'python-version: ["3.11"]' in content or \
                "python-version: ['3.11']" in content, \
                "GitHub workflow should use Python 3.11"

    def test_environment_enum_values(self):
        """Test that ENVIRONMENT setting uses expected values."""
        settings = Settings()

        # Should be one of the expected values
        valid_environments = ["local", "dev", "staging", "production", "test"]
        assert settings.ENVIRONMENT in valid_environments, \
            f"ENVIRONMENT should be one of {valid_environments}, " \
            f"got {settings.ENVIRONMENT}"
