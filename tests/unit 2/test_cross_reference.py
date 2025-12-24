"""Cross-reference tests between different configurations."""
import pytest
from pathlib import Path

from app.core.config import Settings


class TestCrossReference:
    """Test that different configurations are consistent with each other."""

    def test_api_prefix_consistency(self):
        """Test API prefix is used consistently."""
        settings = Settings()
        api_prefix = settings.API_V1_STR

        # Should start with /
        assert api_prefix.startswith("/"), "API prefix should start with /"

        # Should not end with /
        assert not api_prefix.endswith("/"), "API prefix should not end with /"

        # Common pattern is /api/v1
        assert "api" in api_prefix, "API prefix should contain 'api'"
        assert "v" in api_prefix, "API prefix should contain version (v)"

    def test_cors_origins_valid(self):
        """Test CORS origins are valid URLs."""
        settings = Settings()

        for origin in settings.CORS_ORIGINS:
            # Should be a valid URL
            assert origin.startswith(("http://", "https://")), \
                f"CORS origin {origin} should start with http:// or https://"

            # Production origins should use HTTPS
            if "localhost" not in origin and "127.0.0.1" not in origin:
                assert origin.startswith("https://"), \
                    f"Production CORS origin {origin} should use HTTPS"

    def test_project_name_matches(self):
        """Test project name is consistent across configs."""
        settings = Settings()

        # Project name should match expected pattern
        assert settings.PROJECT_NAME.lower() == "ghostline api", \
            "PROJECT_NAME should be 'Ghostline API'"

    def test_no_hardcoded_api_paths(self):
        """Test that code doesn't hardcode API paths."""
        # Check main.py doesn't hardcode /api/v1
        main_path = Path(__file__).parent.parent.parent / "app" / "main.py"

        if not main_path.exists():
            pytest.skip("main.py not found")

        with open(main_path) as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if '"/api/v1"' in line and 'API_V1_STR' not in line and '#' not in line:
                pytest.fail(
                    f"Line {i+1} in main.py hardcodes /api/v1 "
                    f"instead of using settings.API_V1_STR"
                )

    def test_database_url_format(self):
        """Test DATABASE_URL is properly formatted."""
        settings = Settings()
        db_url = str(settings.DATABASE_URL)

        # Should start with postgresql://
        assert db_url.startswith("postgresql://"), \
            "DATABASE_URL should use postgresql:// scheme"

        # Should not contain hardcoded passwords in the default
        if settings.ENVIRONMENT == "local":
            # Local can have simple passwords
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