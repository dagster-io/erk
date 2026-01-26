---
title: Command Group Testing
read_when:
  - "testing Click command groups"
  - "migrating tests for grouped commands"
  - "testing invoke_without_command patterns"
---

# Command Group Testing

This document covers testing patterns for Click command groups, especially those using `invoke_without_command=True`.

## Test Invocation Changes

When commands are unified into groups, test invocations must change:

### Before (Separate Commands)

```python
# Old: separate remote command
result = runner.invoke(cli, ["pr", "address-remote", "123"], obj=ctx)
```

### After (Grouped Commands)

```python
# New: remote as subcommand
result = runner.invoke(cli, ["pr", "address", "remote", "123"], obj=ctx)
```

## Testing Both Variants

For command groups with default behavior, test both invocation paths:

```python
class TestAddressGroup:
    """Tests for erk pr address command group."""

    def test_local_variant_default(self, tmp_path: Path) -> None:
        """Test invoking group directly runs local variant."""
        runner = CliRunner()
        ctx = ErkContext.for_test(cwd=tmp_path)

        # Invoke group without subcommand
        result = runner.invoke(
            cli,
            ["pr", "address", "--dangerous"],
            obj=ctx,
        )
        # Verify local behavior executed
        ...

    def test_remote_variant_explicit(self, tmp_path: Path) -> None:
        """Test invoking remote subcommand explicitly."""
        runner = CliRunner()
        ctx = ErkContext.for_test(cwd=tmp_path)

        # Invoke with remote subcommand
        result = runner.invoke(
            cli,
            ["pr", "address", "remote", "123"],
            obj=ctx,
        )
        # Verify remote behavior executed
        ...
```

## Bulk Migration with sed

When migrating many tests after command unification:

```bash
# Replace old invocation pattern with new
find tests/ -name "*.py" -exec sed -i \
  's/"address-remote", "/"address", "remote", "/g' {} \;
```

## Testing Default vs Subcommand Behavior

Groups with `invoke_without_command=True` need explicit testing of both paths:

```python
def test_group_default_behavior(tmp_path: Path) -> None:
    """Verify default behavior when no subcommand given."""
    runner = CliRunner()

    # Missing required flag should fail
    result = runner.invoke(cli, ["pr", "address"], obj=ctx)
    assert result.exit_code != 0
    assert "--dangerous" in result.output

    # With required flag, runs local
    result = runner.invoke(cli, ["pr", "address", "--dangerous"], obj=ctx)
    assert result.exit_code == 0


def test_group_subcommand_behavior(tmp_path: Path) -> None:
    """Verify subcommand takes precedence."""
    runner = CliRunner()

    # Remote subcommand ignores group options
    result = runner.invoke(cli, ["pr", "address", "remote", "123"], obj=ctx)
    assert result.exit_code == 0
```

## Common Pitfalls

### Forgetting to Update Test Invocations

After unifying commands, tests using the old path will fail:

```python
# FAILS after migration
result = runner.invoke(cli, ["pr", "address-remote", "123"], obj=ctx)
# Error: No such command 'address-remote'
```

### Testing Group Options on Subcommand

Group-level options don't propagate to subcommands by default:

```python
# Group option --dangerous doesn't apply to remote subcommand
result = runner.invoke(
    cli,
    ["pr", "address", "--dangerous", "remote", "123"],  # --dangerous ignored
    obj=ctx,
)
```

### Missing Context for Grouped Commands

Grouped commands may need different context setup:

```python
# Local variant needs Claude executor
ctx = ErkContext.for_test(cwd=tmp_path, claude_executor=FakeClaudeExecutor())

# Remote variant needs GitHub access
ctx = ErkContext.for_test(cwd=tmp_path, github=FakeGitHub())
```

## Related Documentation

- [Local/Remote Command Groups](../cli/local-remote-command-groups.md) - Implementation pattern
- [Exec Script Testing](exec-script-testing.md) - General exec testing patterns
- [CLI Testing Patterns](cli-testing.md) - Broader CLI testing guidance
