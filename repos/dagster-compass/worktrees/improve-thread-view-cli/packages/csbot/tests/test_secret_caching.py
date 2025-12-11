"""Tests for secret caching in get_jinja_template_context_with_secret_store.

This test ensures that the @cache decorator on the nested functions within
get_jinja_template_context_with_secret_store properly isolates caching by
organization ID and does not leak secrets across organizations.
"""

from pathlib import Path

from csbot.slackbot.slackbot_core import get_jinja_template_context_with_secret_store
from csbot.slackbot.slackbot_secrets import SecretStore


class MockSecretStore(SecretStore):
    """Mock secret store that tracks calls and returns org-specific secrets."""

    def __init__(self):
        self.get_secret_calls: list[tuple[int, str]] = []
        self.store_secret_calls: list[tuple[int, str, str]] = []

    async def get_secret_contents(self, org_id: int, key: str) -> str:
        """Return org-specific secret content."""
        self.get_secret_calls.append((org_id, key))
        return f"secret-for-org-{org_id}-key-{key}"

    async def store_secret(self, org_id: int, key: str, contents: str) -> Path:
        """Store secret (not used in these tests)."""
        self.store_secret_calls.append((org_id, key, contents))
        return Path(f"/tmp/org_{org_id}_{key}")


class TestSecretCachingAcrossOrganizations:
    """Test that secret caching does not leak across organizations."""

    def test_pull_from_secret_manager_to_file_does_not_cache_across_orgs(self):
        """Test that pull_from_secret_manager_to_file returns different files for different orgs."""
        mock_store = MockSecretStore()
        root = Path("/tmp/test")

        # Get context for org 1
        context1 = get_jinja_template_context_with_secret_store(root, mock_store, org_id=1)
        pull_to_file1 = context1["pull_from_secret_manager_to_file"]

        # Get context for org 2
        context2 = get_jinja_template_context_with_secret_store(root, mock_store, org_id=2)
        pull_to_file2 = context2["pull_from_secret_manager_to_file"]

        # Pull the same secret name for both orgs
        file1 = pull_to_file1("github_private_key")
        file2 = pull_to_file2("github_private_key")

        # Read the contents of both files
        content1 = Path(file1).read_text()
        content2 = Path(file2).read_text()

        # The contents should be different (org-specific)
        assert content1 == "secret-for-org-1-key-github_private_key"
        assert content2 == "secret-for-org-2-key-github_private_key"
        assert content1 != content2

        # Verify that the secret store was called twice (once for each org)
        assert len(mock_store.get_secret_calls) == 2
        assert (1, "github_private_key") in mock_store.get_secret_calls
        assert (2, "github_private_key") in mock_store.get_secret_calls

    def test_pull_from_secret_manager_to_string_does_not_cache_across_orgs(self):
        """Test that pull_from_secret_manager_to_string returns different values for different orgs."""
        mock_store = MockSecretStore()
        root = Path("/tmp/test")

        # Get context for org 1
        context1 = get_jinja_template_context_with_secret_store(root, mock_store, org_id=1)
        pull_to_string1 = context1["pull_from_secret_manager_to_string"]

        # Get context for org 2
        context2 = get_jinja_template_context_with_secret_store(root, mock_store, org_id=2)
        pull_to_string2 = context2["pull_from_secret_manager_to_string"]

        # Pull the same secret name for both orgs
        secret1 = pull_to_string1("stripe_api_key")
        secret2 = pull_to_string2("stripe_api_key")

        # The secrets should be different (org-specific)
        assert secret1 == "secret-for-org-1-key-stripe_api_key"
        assert secret2 == "secret-for-org-2-key-stripe_api_key"
        assert secret1 != secret2

        # Verify that the secret store was called twice (once for each org)
        assert len(mock_store.get_secret_calls) == 2
        assert (1, "stripe_api_key") in mock_store.get_secret_calls
        assert (2, "stripe_api_key") in mock_store.get_secret_calls

    def test_caching_works_within_same_org(self):
        """Test that caching works correctly for repeated calls within the same org."""
        mock_store = MockSecretStore()
        root = Path("/tmp/test")

        # Get context for org 1
        context = get_jinja_template_context_with_secret_store(root, mock_store, org_id=1)
        pull_to_string = context["pull_from_secret_manager_to_string"]

        # Pull the same secret multiple times
        secret1 = pull_to_string("api_key")
        secret2 = pull_to_string("api_key")
        secret3 = pull_to_string("api_key")

        # All should return the same value
        assert secret1 == secret2 == secret3
        assert secret1 == "secret-for-org-1-key-api_key"

        # Verify that the secret store was called only once (caching worked)
        assert len(mock_store.get_secret_calls) == 1
        assert mock_store.get_secret_calls[0] == (1, "api_key")

    def test_different_secrets_not_cached_together(self):
        """Test that different secret names are cached separately."""
        mock_store = MockSecretStore()
        root = Path("/tmp/test")

        # Get context for org 1
        context = get_jinja_template_context_with_secret_store(root, mock_store, org_id=1)
        pull_to_string = context["pull_from_secret_manager_to_string"]

        # Pull different secrets
        secret1 = pull_to_string("key1")
        secret2 = pull_to_string("key2")
        secret3 = pull_to_string("key1")  # Same as first

        # Verify correct values
        assert secret1 == "secret-for-org-1-key-key1"
        assert secret2 == "secret-for-org-1-key-key2"
        assert secret3 == "secret-for-org-1-key-key1"

        # Verify that the secret store was called twice (once for each unique key)
        assert len(mock_store.get_secret_calls) == 2
        assert (1, "key1") in mock_store.get_secret_calls
        assert (1, "key2") in mock_store.get_secret_calls
