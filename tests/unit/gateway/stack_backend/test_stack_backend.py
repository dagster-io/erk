"""Tests for StackBackend implementations."""


def test_simple_stack_backend_returns_false() -> None:
    """SimpleStackBackend.is_stacking_enabled() returns False."""
    from erk_shared.gateway.stack_backend.simple import SimpleStackBackend

    backend = SimpleStackBackend()
    assert backend.is_stacking_enabled() is False


def test_graphite_compat_stack_backend_returns_true() -> None:
    """GraphiteCompatStackBackend.is_stacking_enabled() returns True."""
    from erk_shared.gateway.stack_backend.graphite_compat import GraphiteCompatStackBackend

    backend = GraphiteCompatStackBackend()
    assert backend.is_stacking_enabled() is True


def test_fake_stack_backend_enabled() -> None:
    """FakeStackBackend with stacking_enabled=True returns True."""
    from erk_shared.gateway.stack_backend.fake import FakeStackBackend

    backend = FakeStackBackend(stacking_enabled=True)
    assert backend.is_stacking_enabled() is True


def test_fake_stack_backend_disabled() -> None:
    """FakeStackBackend with stacking_enabled=False returns False."""
    from erk_shared.gateway.stack_backend.fake import FakeStackBackend

    backend = FakeStackBackend(stacking_enabled=False)
    assert backend.is_stacking_enabled() is False
