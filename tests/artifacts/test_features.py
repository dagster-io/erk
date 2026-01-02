"""Tests for optional features registry."""

from erk.artifacts.features import AVAILABLE_FEATURES, Feature, get_feature, list_features


def test_feature_dataclass_is_frozen() -> None:
    """Feature dataclass is immutable."""
    feature = Feature(
        name="test",
        description="Test feature",
        workflows=frozenset({"test.yml"}),
    )

    # Should raise on attribute assignment
    try:
        feature.name = "changed"  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except AttributeError:
        pass


def test_get_feature_returns_existing_feature() -> None:
    """get_feature returns feature when it exists."""
    feature = get_feature("dignified-review")

    assert feature is not None
    assert feature.name == "dignified-review"
    assert "dignified-python-review.yml" in feature.workflows


def test_get_feature_returns_none_for_unknown() -> None:
    """get_feature returns None for unknown feature names."""
    result = get_feature("nonexistent-feature")
    assert result is None


def test_list_features_returns_all_features() -> None:
    """list_features returns all available features."""
    features = list_features()

    assert len(features) >= 1
    names = {f.name for f in features}
    assert "dignified-review" in names


def test_available_features_contains_dignified_review() -> None:
    """AVAILABLE_FEATURES contains dignified-review."""
    assert "dignified-review" in AVAILABLE_FEATURES
    feature = AVAILABLE_FEATURES["dignified-review"]
    assert feature.description != ""
