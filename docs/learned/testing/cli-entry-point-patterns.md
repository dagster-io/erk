---
title: CLI Entry Point Testing Patterns
read_when:
  - writing tests for CLI entry points
  - testing Click-based main() functions
  - testing command initialization code
tripwires:
  - action: "writing tests for CLI entry points"
    warning: "CLI entry points are Layer 3 pure unit tests. Use mocking (not CliRunner) to keep tests simple and focused. Signs you're over-engineering: using CliRunner for simple output functions, creating fixtures, test file 20+ lines for one call, multiple nested context managers."
---

# CLI Entry Point Testing Patterns

## The Problem

CLI entry points appear complex because they involve the Click framework, leading to over-engineered tests. However, when the entry point has no gateway dependencies, it's actually a Layer 3 pure unit test that should use simple mocking instead of CliRunner.

## Simplified Pattern (Recommended)

For entry points that only perform output and initialization (no gateway dependencies), use pure mocking:

```python
from unittest.mock import patch

def test_main_prints_greeting():
    """Test that main() outputs the greeting."""
    with patch("erk.click.echo") as mock_echo, \
         patch("erk.cli"):
        from erk import main
        main()
        mock_echo.assert_called_once_with("Hello from erk")
```

**11 lines total** - Simple, focused, and tests exactly what matters.

## Why Not CliRunner?

The `CliRunner` approach is over-engineered for simple entry point tests:

```python
# ❌ WRONG: Over-engineered for simple output testing (20+ lines)
from click.testing import CliRunner

def test_main_prints_greeting():
    """Test that main() outputs the greeting."""
    with patch("erk.cli") as mock_cli, \
         patch("erk.some_module") as mock_module:
        runner = CliRunner()
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert "Hello from erk" in result.output
```

Problems with this approach:

- Creates unnecessary `CliRunner` fixture
- Tests implementation details (exit code)
- Multiple nested context managers
- Test file grows to 20+ lines for a single function call

## When to Use CliRunner

Reserve `CliRunner` for tests that actually need it:

- Testing CLI argument parsing
- Testing command invocation chains
- Testing complex Click options and flags
- Testing command groups and subcommands

## Layer Classification

CLI entry points without gateway dependencies are **Layer 3 (pure unit tests)**, not Layer 5 (integration tests):

- **No external I/O**: Just printing output
- **No gateway calls**: No filesystem, network, or subprocess operations
- **Pure logic**: Deterministic behavior

Use mocking to keep Layer 3 tests simple and fast.

## Real Example

From the "add a print statement" implementation:

**Original over-engineered approach**: 20+ lines with `CliRunner`, multiple fixtures
**Corrected approach**: 11 lines with simple mocking

The corrected version tests the exact same behavior but is:

- Easier to read and maintain
- Faster to execute
- More focused on what actually matters

## Key Takeaways

1. **CLI context doesn't mean complexity**: Entry points without gateways are Layer 3
2. **Mock, don't invoke**: Use `patch()` for simple output tests
3. **Save CliRunner for real CLI testing**: Argument parsing, command chains, option handling
4. **Watch for over-engineering signals**: 20+ line tests, nested fixtures, multiple context managers

## Related Documentation

- [Test Layer Misidentification Tripwire](tripwires.md#cli-entry-point-layer-misidentification)
- [Fake-Driven Testing 5-Layer Architecture](../testing/testing.md)
