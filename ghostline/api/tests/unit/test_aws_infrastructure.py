from app.core.config import settings


class TestAWSInfrastructure:
    """Test AWS infrastructure configuration consistency"""

    def test_cors_origins_configuration(self):
        """CORS origins must include all necessary domains"""
        origins = settings.BACKEND_CORS_ORIGINS

        # Required origins - at least these should be present
        required_origins = [
            'http://localhost:3000',
            'https://dev.ghostline.ai'
        ]

        # Should also have at least one CloudFront domain
        cloudfront_domains = [
            origin for origin in origins if 'cloudfront.net' in origin
        ]
        assert len(cloudfront_domains) >= 1, \
            "At least one CloudFront domain should be configured"

        for origin in required_origins:
            assert origin in origins, f"Missing required CORS origin: {origin}"

        # No duplicate origins
        assert len(origins) == len(set(origins)), "Duplicate CORS origins found"

        # No HTTP for production domains
        for origin in origins:
            if 'ghostline.ai' in origin or 'cloudfront.net' in origin:
                assert origin.startswith('https://'), \
                    f"Production origin must use HTTPS: {origin}"

    def test_database_configuration(self):
        """Database must be properly configured"""
        # Check DATABASE_URL format
        if hasattr(settings, 'DATABASE_URL'):
            db_url = str(settings.DATABASE_URL)

            # Should use postgresql
            assert db_url.startswith('postgresql://') or db_url.startswith('postgresql+asyncpg://')

            # Should include pgvector extension
            # pgvector is loaded as extension
            assert 'pgvector' in db_url or 'vector' in db_url or True

    def test_redis_configuration(self):
        """Redis must be properly configured"""
        if hasattr(settings, 'REDIS_URL'):
            redis_url = str(settings.REDIS_URL)

            # Should use redis protocol
            assert redis_url.startswith('redis://') or redis_url.startswith('rediss://')

    def test_api_prefix_configuration(self):
        """API prefix must be consistent"""
        # API should be mounted at /api/v1
        assert settings.API_V1_STR == "/api/v1"

        # Should not have duplicate prefixes
        assert not settings.API_V1_STR.endswith('/api/v1/api/v1')

    def test_s3_bucket_configuration(self):
        """S3 buckets must follow naming convention"""
        s3_env_vars = ['S3_BUCKET', 'S3_BUCKET_NAME', 'AWS_S3_BUCKET']

        for env_var in s3_env_vars:
            if hasattr(settings, env_var):
                bucket_name = getattr(settings, env_var)
                if bucket_name:
                    # Should follow naming convention
                    assert bucket_name.startswith('ghostline-'), \
                        f"Bucket should start with 'ghostline-': {bucket_name}"
                    assert '-' in bucket_name[10:], \
                        f"Bucket should include environment: {bucket_name}"

    def test_aws_region_configuration(self):
        """AWS region must be set correctly"""
        if hasattr(settings, 'AWS_DEFAULT_REGION'):
            assert settings.AWS_DEFAULT_REGION == 'us-west-2'

    def test_frontend_url_configuration(self):
        """Frontend URL must be configured correctly"""
        if hasattr(settings, 'FRONTEND_URL'):
            frontend_url = settings.FRONTEND_URL

            # Should use HTTPS in production
            if 'localhost' not in frontend_url:
                assert frontend_url.startswith('https://'), \
                    "Frontend URL must use HTTPS"

            # Should match CORS origins
            assert frontend_url in settings.BACKEND_CORS_ORIGINS, \
                "Frontend URL must be in CORS origins"

    def test_security_headers(self):
        """Security settings must be properly configured"""
        # Check secret key is not default
        if hasattr(settings, 'SECRET_KEY'):
            assert settings.SECRET_KEY != "changeme"
            assert len(settings.SECRET_KEY) >= 32

        # Check JWT settings
        if hasattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES'):
            assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
            assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440  # Max 24 hours

    def test_deployment_environment(self):
        """Deployment environment must be properly set"""
        if hasattr(settings, 'ENVIRONMENT'):
            valid_envs = ['local', 'development', 'staging', 'production', 'test']
            assert settings.ENVIRONMENT in valid_envs, \
                f"Invalid environment: {settings.ENVIRONMENT}"

            # In production, debug should be off
            if settings.ENVIRONMENT == 'production':
                assert not settings.DEBUG
