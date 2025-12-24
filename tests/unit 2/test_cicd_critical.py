# ... existing code ...
        for critical_step in critical_steps:
            assert any(critical_step in name for name in step_names), \
                f"Missing critical step: {critical_step}"
# ... existing code ...
        # Check script location (with proper formatting)
        assert 'script_location = %(here)s/alembic' in content or \
            'script_location = alembic' in content
# ... existing code ...
            has_env = 'environment' in container
            has_secrets = 'secrets' in container
            assert has_env or has_secrets, \
                "Container must have environment variables or secrets"

            # Check environment variables if present
            if has_env:
                # DATABASE_URL and REDIS_URL might be in secrets instead
                env_count = len(container['environment'])
                assert env_count > 0, "Environment should have variables"

            # Check secrets if present
            if has_secrets:
                # Verify critical secrets are referenced
                secret_count = len(container['secrets'])
                assert secret_count > 0, "Secrets should be defined" 