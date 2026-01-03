"""Tests for forward reference detection utilities.

These are Layer 3 (pure unit tests) that verify the AST parsing logic
works correctly on known inputs. No external dependencies, no fakes.

This ensures our detection logic is correct before we trust it to find
violations in the erk codebase.
"""

from __future__ import annotations

import ast

from erk_dev.forward_refs.detection import (
    check_source,
    has_future_annotations,
    has_type_checking_imports,
)


class TestHasTypeCheckingImports:
    """Tests for has_type_checking_imports detection."""

    def test_detects_bare_type_checking_with_import(self) -> None:
        """Detects `if TYPE_CHECKING:` with import inside."""
        source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType
"""
        tree = ast.parse(source)
        assert has_type_checking_imports(tree) is True

    def test_detects_qualified_type_checking_with_import(self) -> None:
        """Detects `if typing.TYPE_CHECKING:` with import inside."""
        source = """
import typing

if typing.TYPE_CHECKING:
    from mymodule import MyType
"""
        tree = ast.parse(source)
        assert has_type_checking_imports(tree) is True

    def test_false_when_no_type_checking_block(self) -> None:
        """Returns False when no TYPE_CHECKING block exists."""
        source = """
from mymodule import MyType

def process(x: MyType) -> MyType:
    return x
"""
        tree = ast.parse(source)
        assert has_type_checking_imports(tree) is False

    def test_false_when_type_checking_block_has_no_imports(self) -> None:
        """Returns False when TYPE_CHECKING block has no imports."""
        source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    x = 1  # Not an import
"""
        tree = ast.parse(source)
        assert has_type_checking_imports(tree) is False

    def test_false_when_import_outside_type_checking(self) -> None:
        """Returns False when imports are outside TYPE_CHECKING block."""
        source = """
from typing import TYPE_CHECKING
from mymodule import MyType  # Outside TYPE_CHECKING

if TYPE_CHECKING:
    x = 1  # No import here
"""
        tree = ast.parse(source)
        assert has_type_checking_imports(tree) is False

    def test_detects_regular_import_in_type_checking(self) -> None:
        """Detects `import foo` (not just `from foo import bar`)."""
        source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import mymodule
"""
        tree = ast.parse(source)
        assert has_type_checking_imports(tree) is True


class TestHasFutureAnnotations:
    """Tests for has_future_annotations detection."""

    def test_detects_future_annotations(self) -> None:
        """Detects `from __future__ import annotations`."""
        source = """
from __future__ import annotations

from typing import TYPE_CHECKING
"""
        tree = ast.parse(source)
        assert has_future_annotations(tree) is True

    def test_detects_future_annotations_with_other_imports(self) -> None:
        """Detects when annotations is among other future imports."""
        source = """
from __future__ import annotations, division
"""
        tree = ast.parse(source)
        assert has_future_annotations(tree) is True

    def test_false_when_no_future_import(self) -> None:
        """Returns False when no __future__ import exists."""
        source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType
"""
        tree = ast.parse(source)
        assert has_future_annotations(tree) is False

    def test_false_when_future_import_without_annotations(self) -> None:
        """Returns False when __future__ import lacks annotations."""
        source = """
from __future__ import division

from typing import TYPE_CHECKING
"""
        tree = ast.parse(source)
        assert has_future_annotations(tree) is False


class TestCheckSource:
    """Tests for check_source combined detection."""

    def test_returns_violation_for_risky_pattern(self) -> None:
        """Returns violation when TYPE_CHECKING import lacks future annotations."""
        source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType

def process(x: MyType) -> MyType:
    return x
"""
        result = check_source(source)
        assert result is not None
        assert "TYPE_CHECKING" in result.message

    def test_returns_none_when_safe(self) -> None:
        """Returns None when future annotations are present."""
        source = """
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType

def process(x: MyType) -> MyType:
    return x
"""
        result = check_source(source)
        assert result is None

    def test_returns_none_when_no_type_checking(self) -> None:
        """Returns None when no TYPE_CHECKING imports exist."""
        source = """
from mymodule import MyType

def process(x: MyType) -> MyType:
    return x
"""
        result = check_source(source)
        assert result is None

    def test_returns_none_for_syntax_error(self) -> None:
        """Returns None when source has syntax errors."""
        source = """
def broken(
    # missing closing paren
"""
        result = check_source(source)
        assert result is None

    def test_empty_source_is_safe(self) -> None:
        """Empty source is safe (no violations)."""
        result = check_source("")
        assert result is None
