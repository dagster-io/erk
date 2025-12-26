"""Test render.yaml configuration against staging configuration for environment variable completeness."""

import re
import subprocess
from pathlib import Path

import yaml

# Environment variables that are excluded from temporal worker validation
TEMPORAL_WORKER_EXCLUDED_ENV_VARS = {
    "HTTP_HOST",  # Temporal workers don't serve HTTP
    "HTTP_PORT",  # Temporal workers don't serve HTTP
}


class TestRenderConfigValidation:
    """Test that render.yaml has all necessary environment variables from staging config."""

    @staticmethod
    def _extract_env_vars_from_staging_config():
        """Extract all environment variables referenced in staging.csbot.config.yaml."""
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        staging_config_path = repo_root / "staging.csbot.config.yaml"

        with open(staging_config_path) as f:
            content = f.read()

        # Find all {{ env('VAR_NAME') }} and {{ secret('key', 'ENV_VAR') }} patterns
        env_vars = set()

        # Pattern for {{ env('VAR_NAME') }} or {{ env('VAR_NAME', 'default') }}
        env_pattern = r"\{\{\s*env\(['\"](.*?)['\"]"
        env_matches = re.findall(env_pattern, content)
        env_vars.update(env_matches)

        # Pattern for {{ secret('key', 'ENV_VAR') }}
        secret_pattern = r"\{\{\s*secret\(['\"]\w+['\"]\s*,\s*['\"](.*?)['\"]\s*\)\s*\}\}"
        secret_matches = re.findall(secret_pattern, content)
        env_vars.update(secret_matches)

        return env_vars

    @staticmethod
    def _extract_env_vars_from_render_yaml():
        """Extract environment variables defined in render.yaml services."""
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        render_config_path = repo_root / "render.yaml"

        with open(render_config_path) as f:
            render_config = yaml.safe_load(f)

        services = {}

        for service in render_config.get("services", []):
            service_name = service.get("name")
            if service_name in [
                "compass-bot",
                "compass-admin-panel-staging",
                "staging-temporal-worker",
                "staging-temporal-worker-monitoring",
            ]:
                env_vars = set()
                for env_var in service.get("envVars", []):
                    key = env_var.get("key")
                    if key:
                        env_vars.add(key)
                services[service_name] = env_vars

        return services

    def test_compass_bot_has_all_staging_env_vars(self):
        """Test that compass-bot service has all environment variables from staging config."""
        staging_env_vars = self._extract_env_vars_from_staging_config()
        render_services = self._extract_env_vars_from_render_yaml()

        compass_bot_env_vars = render_services.get("compass-bot", set())

        # RENDER_SERVICE_ID is only used by secret_store config, not needed in services
        staging_env_vars_filtered = staging_env_vars - {"RENDER_SERVICE_ID"}
        missing_vars = staging_env_vars_filtered - compass_bot_env_vars

        assert not missing_vars, (
            f"compass-bot service is missing these environment variables "
            f"that are used in staging.csbot.config.yaml: {sorted(missing_vars)}"
        )

    def test_compass_admin_panel_has_all_staging_env_vars(self):
        """Test that compass-admin-panel-staging service has all environment variables from staging config."""
        staging_env_vars = self._extract_env_vars_from_staging_config()
        render_services = self._extract_env_vars_from_render_yaml()

        admin_panel_env_vars = render_services.get("compass-admin-panel-staging", set())

        # RENDER_SERVICE_ID is only used by secret_store config, not needed in services
        staging_env_vars_filtered = staging_env_vars - {"RENDER_SERVICE_ID"}
        missing_vars = staging_env_vars_filtered - admin_panel_env_vars

        assert not missing_vars, (
            f"compass-admin-panel-staging service is missing these environment variables "
            f"that are used in staging.csbot.config.yaml: {sorted(missing_vars)}"
        )

    def test_staging_temporal_worker_has_all_staging_env_vars(self):
        """Test that staging-temporal-worker service has all environment variables from staging config."""
        staging_env_vars = self._extract_env_vars_from_staging_config()
        render_services = self._extract_env_vars_from_render_yaml()

        temporal_worker_env_vars = render_services.get("staging-temporal-worker", set())

        staging_env_vars_filtered = staging_env_vars - TEMPORAL_WORKER_EXCLUDED_ENV_VARS
        missing_vars = staging_env_vars_filtered - temporal_worker_env_vars

        assert not missing_vars, (
            f"staging-temporal-worker service is missing these environment variables "
            f"that are used in staging.csbot.config.yaml: {sorted(missing_vars)}"
        )

    def test_staging_temporal_worker_monitoring_has_all_staging_env_vars(self):
        """Test that staging-temporal-worker-monitoring service has all environment variables from staging config."""
        staging_env_vars = self._extract_env_vars_from_staging_config()
        render_services = self._extract_env_vars_from_render_yaml()

        temporal_worker_env_vars = render_services.get("staging-temporal-worker-monitoring", set())

        staging_env_vars_filtered = staging_env_vars - TEMPORAL_WORKER_EXCLUDED_ENV_VARS
        missing_vars = staging_env_vars_filtered - temporal_worker_env_vars

        assert not missing_vars, (
            f"staging-temporal-worker-monitoring service is missing these environment variables "
            f"that are used in staging.csbot.config.yaml: {sorted(missing_vars)}"
        )

    def test_render_services_exist_in_config(self):
        """Test that all expected services exist in render.yaml."""
        render_services = self._extract_env_vars_from_render_yaml()

        assert "compass-bot" in render_services, "compass-bot service not found in render.yaml"
        assert "compass-admin-panel-staging" in render_services, (
            "compass-admin-panel-staging service not found in render.yaml"
        )
        assert "staging-temporal-worker" in render_services, (
            "staging-temporal-worker service not found in render.yaml"
        )
        assert "staging-temporal-worker-monitoring" in render_services, (
            "staging-temporal-worker-monitoring service not found in render.yaml"
        )

    def test_staging_config_has_expected_env_vars(self):
        """Test that staging config extraction finds expected environment variables."""
        staging_env_vars = self._extract_env_vars_from_staging_config()

        # Check for some known env vars to ensure parsing is working
        expected_vars = {
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "SLACK_SIGNING_SECRET",
            "DATABASE_URL",
            "JWT_SECRET",
        }

        missing_expected = expected_vars - staging_env_vars
        assert not missing_expected, (
            f"Failed to extract these expected environment variables from staging config: {missing_expected}"
        )

    def test_render_yaml_matches_template(self):
        """Test that render.yaml matches the generated output from render.yaml.jinja."""
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        render_yaml_path = repo_root / "render.yaml"
        template_path = repo_root / "render.yaml.jinja"

        if not template_path.exists():  # Template doesn't exist, skip test
            return

        # Read current render.yaml
        with open(render_yaml_path, encoding="utf-8") as f:
            current_content = f.read()

        # Generate from template
        result = subprocess.run(
            ["uv", "run", "scripts/generate_render_yaml.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception, check return code manually
        )

        if result.returncode != 0:  # Generation script failed
            raise AssertionError(
                f"Failed to generate render.yaml from template:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        # Read generated render.yaml
        with open(render_yaml_path, encoding="utf-8") as f:
            generated_content = f.read()

        # Compare
        if current_content != generated_content:  # Content differs
            # Restore original
            with open(render_yaml_path, "w", encoding="utf-8") as f:
                f.write(current_content)

            raise AssertionError(
                "render.yaml does not match the template output. "
                "Run 'uv run scripts/generate_render_yaml.py' to regenerate it from render.yaml.jinja"
            )
