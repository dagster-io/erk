"""Tests for graphite types module."""

from erk_shared.gateway.graphite.types import BranchMetadata


class TestBranchMetadata:
    """Tests for BranchMetadata dataclass."""

    def test_trunk_factory_creates_trunk_branch(self) -> None:
        metadata = BranchMetadata.trunk("main")
        assert metadata.name == "main"
        assert metadata.parent is None
        assert metadata.is_trunk is True
        assert metadata.children == []

    def test_branch_factory_creates_feature_branch(self) -> None:
        metadata = BranchMetadata.branch("feature", parent="main")
        assert metadata.name == "feature"
        assert metadata.parent == "main"
        assert metadata.is_trunk is False
        assert metadata.children == []

    def test_trunk_with_children(self) -> None:
        metadata = BranchMetadata.trunk("main", children=["feature-1", "feature-2"])
        assert metadata.children == ["feature-1", "feature-2"]

    def test_branch_with_children(self) -> None:
        metadata = BranchMetadata.branch("feature", parent="main", children=["sub"])
        assert metadata.children == ["sub"]
