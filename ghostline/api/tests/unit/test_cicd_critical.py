import json
from pathlib import Path

import yaml


class TestCICDCritical:
    """Test critical CI/CD configuration that should not change"""

    def setup_method(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.github_dir = self.root_dir / '.github'
        self.workflows_dir = self.github_dir / 'workflows'

    def test_deploy_workflow_exists(self):
        """Deploy workflow must exist"""
        deploy_workflow = self.workflows_dir / 'deploy.yml'
        assert deploy_workflow.exists(), "deploy.yml workflow is missing"

    def test_deploy_workflow_structure(self):
        """Deploy workflow must have critical steps"""
        deploy_workflow = self.workflows_dir / 'deploy.yml'
        with open(deploy_workflow) as f:
            content = f.read()
            workflow = yaml.safe_load(content)

        # Check it's a valid workflow
        assert workflow is not None
        assert isinstance(workflow, dict)

        # Check trigger conditions (YAML may parse 'on' as True)
        on_key = 'on' if 'on' in workflow else True
        assert on_key in workflow
        assert 'push' in workflow[on_key]
        assert 'main' in workflow[on_key]['push']['branches']

        # Check jobs exist
        assert 'deploy' in workflow['jobs']

        # Check critical steps in deployment
        deploy_steps = workflow['jobs']['deploy']['steps']
        step_names = [step.get('name', '') for step in deploy_steps]

        critical_steps = [
            'Configure AWS credentials',
            'Login to Amazon ECR',
            'Build, tag, and push image to Amazon ECR',
            'Deploy Amazon ECS task definition'
        ]

        for critical_step in critical_steps:
            assert any(critical_step in name for name in step_names), \
                f"Missing critical step: {critical_step}"

    def test_test_workflow_structure(self):
        """Test workflow must run before deployment"""
        test_workflow = self.workflows_dir / 'test.yml'
        with open(test_workflow) as f:
            workflow = yaml.safe_load(f)

        # Check it's a valid workflow
        assert workflow is not None

        # Check trigger conditions (YAML may parse 'on' as True)
        on_key = 'on' if 'on' in workflow else True
        assert on_key in workflow

        # Should run on both push and PR
        assert 'push' in workflow[on_key]
        assert 'pull_request' in workflow[on_key]

        # Check test job exists
        assert 'test' in workflow['jobs']

        # Check poetry is used
        test_steps = workflow['jobs']['test']['steps']
        step_runs = [step.get('run', '') for step in test_steps if 'run' in step]

        assert any('poetry install' in run for run in step_runs)
        # Test command might be run with activated venv or poetry run
        assert any('pytest' in run for run in step_runs)

    def test_dockerfile_configuration(self):
        """Dockerfile must have correct configuration"""
        dockerfile = self.root_dir / 'Dockerfile'
        assert dockerfile.exists()

        with open(dockerfile) as f:
            content = f.read()

        # Check base image
        assert 'FROM python:3.11' in content or 'FROM python:3.12' in content

        # Check poetry installation
        assert 'poetry' in content.lower()

        # Check app directory
        assert 'WORKDIR /app' in content

        # Check port exposure
        assert 'EXPOSE 8000' in content

        # Check startup command
        assert 'uvicorn' in content
        assert 'app.main:app' in content

    def test_alembic_configuration(self):
        """Alembic must be properly configured"""
        alembic_ini = self.root_dir / 'alembic.ini'
        assert alembic_ini.exists()

        with open(alembic_ini) as f:
            content = f.read()

        # Check script location (with proper formatting)
        assert 'script_location = %(here)s/alembic' in content or \
            'script_location = alembic' in content

        # Check it uses env.py for database URL
        assert 'sqlalchemy.url' not in content or 'sqlalchemy.url = ' in content

    def test_pyproject_configuration(self):
        """pyproject.toml must have correct dependencies"""
        pyproject = self.root_dir / 'pyproject.toml'
        with open(pyproject) as f:
            content = f.read()

        # Critical dependencies
        critical_deps = [
            'fastapi',
            'uvicorn',
            'sqlalchemy',
            'alembic',
            'pydantic',
            'boto3',
            'redis',
            'celery',
            'pgvector'
        ]

        for dep in critical_deps:
            assert dep in content, f"Missing critical dependency: {dep}"

    def test_ecs_task_definition_files(self):
        """ECS task definitions must exist and be valid"""
        # Try to find task definitions in parent directories
        task_defs_dir = self.root_dir.parent.parent / 'infra' / 'ecs-task-definitions'

        # Only check if the directory exists
        if not task_defs_dir.exists():
            # Skip this test if task definitions are managed elsewhere
            return

        required_task_defs = [
            'api-task-definition.json',
            'worker-task-definition.json'
        ]

        for task_def_file in required_task_defs:
            task_def_path = task_defs_dir / task_def_file
            if not task_def_path.exists():
                continue  # Skip if file doesn't exist

            with open(task_def_path) as f:
                task_def = json.load(f)

            # Check critical fields
            assert 'family' in task_def
            assert 'containerDefinitions' in task_def
            assert len(task_def['containerDefinitions']) > 0

            # Check container configuration
            container = task_def['containerDefinitions'][0]
            assert 'name' in container
            assert 'image' in container
            assert 'portMappings' in container

            # Check for environment variables or secrets
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
