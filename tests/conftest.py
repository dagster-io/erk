"""Shared test fixtures and configuration."""

import json
import shutil
import tarfile
import tempfile
from pathlib import Path

import pytest


def load_fixture(fixture_path: str) -> str:
    """Load a fixture file as a string.

    Args:
        fixture_path: Path relative to tests/fixtures/ directory

    Returns:
        Content of the fixture file as a string
    """
    base_path = Path(__file__).parent / "fixtures" / fixture_path
    if not base_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    return base_path.read_text(encoding="utf-8")


def load_json_fixture(fixture_path: str) -> dict:
    """Load a JSON fixture file.

    Args:
        fixture_path: Path relative to tests/fixtures/ directory

    Returns:
        Parsed JSON data as a dictionary
    """
    content = load_fixture(fixture_path)
    return json.loads(content)


@pytest.fixture
def extract_repo_fixture():
    """Fixture that extracts tarred git repositories for testing.

    Returns a function that extracts a repo and returns its path.
    The extracted repo is automatically cleaned up after the test.
    """
    temp_dirs = []

    def extract(fixture_name: str) -> Path:
        """Extract a repository fixture.

        Args:
            fixture_name: Name of the fixture (without .tar.gz extension)

        Returns:
            Path to the extracted repository
        """
        fixture_path = Path(__file__).parent / "fixtures" / "repos" / f"{fixture_name}.tar.gz"
        if not fixture_path.exists():
            raise FileNotFoundError(f"Repository fixture not found: {fixture_name}")

        # Create a temporary directory for extraction
        temp_dir = tempfile.mkdtemp(prefix="test_repo_")
        temp_dirs.append(temp_dir)

        # Extract the tarball
        with tarfile.open(fixture_path, "r:gz") as tar:
            tar.extractall(temp_dir)

        # Return the path to the extracted repo
        # Assume the tarball contains a single directory at the root
        extracted_items = list(Path(temp_dir).iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            return extracted_items[0]
        return Path(temp_dir)

    yield extract

    # Cleanup all temporary directories
    for temp_dir in temp_dirs:
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing.

    Yields:
        Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix="test_workspace_")
    yield Path(temp_dir)
    # Cleanup
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================
# Test Scenario Fixtures
# ===========================
# These fixtures use the WorktreeScenario builder to create common test scenarios
# with pre-configured fakes and contexts. Use these instead of manually constructing
# test setups.


@pytest.fixture
def simple_repo(tmp_path: Path):
    """Repository with just main branch.

    Use this fixture for tests that need minimal setup.

    Returns:
        WorktreeScenario with only main branch
    """
    from tests.test_utils.builders import WorktreeScenario

    return WorktreeScenario(tmp_path).with_main_branch().build()


@pytest.fixture
def repo_with_feature(tmp_path: Path):
    """Repository with main + one feature branch.

    This is the most common test scenario.

    Returns:
        WorktreeScenario with main and feature branches
    """
    from tests.test_utils.builders import WorktreeScenario

    return WorktreeScenario(tmp_path).with_main_branch().with_feature_branch("feature").build()


@pytest.fixture
def repo_with_pr(tmp_path: Path):
    """Repository with feature branch and open PR.

    Returns:
        WorktreeScenario with feature branch and PR #123 (checks passing)
    """
    from tests.test_utils.builders import WorktreeScenario

    return (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feature")
        .with_pr("feature", number=123, checks_passing=True)
        .build()
    )


@pytest.fixture
def graphite_stack_repo(tmp_path: Path):
    """Repository with worktree stack (3 levels).

    Returns:
        WorktreeScenario with main -> level-1 -> level-2 stack
    """
    from tests.test_utils.builders import GraphiteCacheBuilder, WorktreeScenario

    scenario = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("level-1")
        .with_feature_branch("level-2")
        .with_graphite_stack(["main", "level-1", "level-2"])
    )

    # Create graphite cache
    GraphiteCacheBuilder().add_trunk("main", children=["level-1"]).add_branch(
        "level-1", parent="main", children=["level-2"]
    ).add_branch("level-2", parent="level-1").write_to(scenario.git_dir)

    return scenario.build()


@pytest.fixture
def multi_worktree_repo(tmp_path: Path):
    """Repository with 5 worktrees (stress test scenario).

    Returns:
        WorktreeScenario with main + 4 feature branches
    """
    from tests.test_utils.builders import WorktreeScenario

    scenario = WorktreeScenario(tmp_path).with_main_branch()
    for i in range(1, 5):
        scenario.with_feature_branch(f"feature-{i}")
    return scenario.build()


@pytest.fixture
def detached_head_repo(tmp_path: Path):
    """Repository with worktree in detached HEAD state.

    Returns:
        WorktreeScenario with root worktree in detached HEAD
    """
    from tests.test_utils.builders import WorktreeScenario

    scenario = WorktreeScenario(tmp_path).with_main_branch()
    scenario._current_branches[scenario.repo_root] = None  # Detached HEAD
    return scenario.build()


@pytest.fixture
def repo_with_merged_pr(tmp_path: Path):
    """Repository with merged PR (common end state).

    Returns:
        WorktreeScenario with merged-feature branch and merged PR #456
    """
    from tests.test_utils.builders import WorktreeScenario

    return (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("merged-feature")
        .with_pr("merged-feature", number=456, state="MERGED")
        .build()
    )
