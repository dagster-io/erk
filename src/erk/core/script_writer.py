"""Abstraction for activation script writing operations.

This module provides ScriptResult, a self-documenting return type for commands that
generate shell activation scripts. The key insight is that ScriptResult knows how to
output itself correctly to the right stream (stdout vs stderr), preventing an entire
class of shell integration bugs.

## Output Routing Decision Tree

When you have a ScriptResult, choose the appropriate output method:

1. **Shell Integration (--script flag)**: Use `result.output_for_shell_integration()`
   - Routes to stdout via machine_output()
   - Handler parses stdout to get script path
   - Used by: create, checkout, switch, consolidate, sync

2. **User Visibility (verbose mode)**: Use `result.output_path_for_user()`
   - Routes to stderr via user_output()
   - Rarely needed - most commands either use shell integration or don't output path
   - Use case: verbose mode showing where script was written

3. **Advanced (deferred output)**: Save result object, call method later
   - Save full `result` object, not just `result.path`
   - Call output method when ready
   - Used by: sync (conditional output based on worktree changes)

4. **Return to Caller**: Just return `result.path`
   - Use when caller needs the path for further processing
   - No output performed
   - Used by: prepare_cwd_recovery, handler helpers

## Usage Examples

### Immediate Output (Most Common)

```python
result = ctx.script_writer.write_activation_script(
    script_content,
    command_name="checkout",
    comment="Checkout worktree",
)
result.output_for_shell_integration()
```

### Deferred Output (Conditional Logic)

```python
# Save result object for later
script_result = ctx.script_writer.write_activation_script(
    script_content,
    command_name="sync",
    comment="Return to worktree",
)

# ... more logic to decide if directory change is needed ...

if should_output:
    script_result.output_for_shell_integration()
```

### Return to Caller (No Output)

```python
result = ctx.script_writer.write_activation_script(
    script_content,
    command_name="prepare",
    comment="Prepare recovery",
)
return result.path  # Caller will handle output
```

## Migration from Old Pattern

**Old pattern (error-prone):**
```python
result = ctx.script_writer.write_activation_script(...)
machine_output(str(result.path), nl=False)  # Easy to use wrong function
```

**New pattern (self-documenting):**
```python
result = ctx.script_writer.write_activation_script(...)
result.output_for_shell_integration()  # Intent is obvious
```

## Why This Design Prevents Bugs

The old pattern had several problems:

1. **Type System Can't Help**: Both machine_output() and user_output() accept str
2. **Wrong Choice Fails Silently**: Handler shows "no directory change needed"
3. **Bug Manifests Elsewhere**: Error appears in handler.py, not command file
4. **Easy to Forget**: Developer must remember routing rule for each context

The new pattern solves all these problems:

1. **Self-Documenting API**: Method name makes intent obvious
2. **Type-Safe**: Can't accidentally route to wrong stream
3. **Idempotent**: Multiple calls safe (only outputs once)
4. **Fail Fast**: Errors in output routing stay local to command

## Implementation Details

- **Lazy Imports**: Methods import machine_output/user_output inside to avoid circular deps
- **Frozen Dataclass**: Uses object.__setattr__() for idempotency flag
- **No Trailing Newline**: Handler expects stdout without trailing newline (nl=False)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from erk.cli.shell_utils import write_script_to_temp


@dataclass(frozen=True)
class ScriptResult:
    """Result of writing an activation script.

    Attributes:
        path: Path to the script file (may be sentinel in tests)
        content: Full content of the script including headers
        _output_performed: Private flag tracking if output has been performed (for idempotency)
    """

    path: Path
    content: str
    _output_performed: bool = False

    def output_for_shell_integration(self) -> None:
        """Output script path to stdout for shell integration handler.

        This method routes the script path to stdout (machine_output), which is
        where the shell integration handler expects to find it. Commands that
        support the --script flag should call this method after generating an
        activation script.

        Each ScriptResult should output exactly once. Calling this method multiple
        times on the same instance will raise ValueError.

        Examples:
            # Immediate output pattern (most common):
            result = ctx.script_writer.write_activation_script(
                script_content,
                command_name="checkout",
                comment="Checkout worktree",
            )
            result.output_for_shell_integration()

            # Deferred output pattern (when conditional logic needed):
            script_result = ctx.script_writer.write_activation_script(...)
            # ... more logic ...
            if should_activate:
                script_result.output_for_shell_integration()

        Raises:
            ValueError: If output has already been performed for this ScriptResult.
        """
        # Idempotency check
        if self._output_performed:
            raise ValueError(
                "output_for_shell_integration() was already called for this ScriptResult. "
                "Each ScriptResult should output exactly once. "
                "If you need deferred output, save the result and call the method only when ready."
            )

        # Lazy import to avoid circular dependency (cli depends on core)
        from erk_shared.output.output import machine_output

        # Output path to stdout for shell integration handler
        machine_output(str(self.path), nl=False)

        # Mark as performed using object.__setattr__ (dataclass is frozen)
        object.__setattr__(self, "_output_performed", True)

    def output_path_for_user(self) -> None:
        """Output script path to stderr for user visibility.

        This method routes the script path to stderr (user_output), which is
        appropriate for informational messages shown to the user. This is rarely
        needed - most commands either use shell integration (stdout) or don't
        output the path at all.

        Each ScriptResult should output exactly once. Calling this method multiple
        times on the same instance will raise ValueError.

        Examples:
            # Verbose mode showing script location:
            result = ctx.script_writer.write_activation_script(...)
            if verbose:
                result.output_path_for_user()

        Raises:
            ValueError: If output has already been performed for this ScriptResult.
        """
        # Idempotency check
        if self._output_performed:
            raise ValueError(
                "output_path_for_user() was already called for this ScriptResult. "
                "Each ScriptResult should output exactly once. "
                "If you need deferred output, save the result and call the method only when ready."
            )

        # Lazy import to avoid circular dependency (cli depends on core)
        from erk_shared.output.output import user_output

        # Output path to stderr for user visibility
        user_output(str(self.path), nl=False)

        # Mark as performed using object.__setattr__ (dataclass is frozen)
        object.__setattr__(self, "_output_performed", True)

    def __str__(self) -> str:
        """String representation shows path (for debugging/logging)."""
        return str(self.path)


class ScriptWriter(ABC):
    """Operations for writing shell activation scripts.

    This abstraction allows tests to verify script content without
    performing actual filesystem I/O.
    """

    @abstractmethod
    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write activation script and return path and content.

        Args:
            content: The shell script content (without metadata header)
            command_name: Command generating the script (e.g., 'checkout', 'switch')
            comment: Description for the script header

        Returns:
            ScriptResult with path to script and full content
        """


class RealScriptWriter(ScriptWriter):
    """Production implementation that writes real temp files."""

    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write activation script to temp file.

        Args:
            content: The shell script content
            command_name: Command generating the script
            comment: Description for the script header

        Returns:
            ScriptResult with path to created temp file and full content
        """
        script_path = write_script_to_temp(
            content,
            command_name=command_name,
            comment=comment,
        )

        # Read back the full content that was written (includes headers)
        full_content = script_path.read_text(encoding="utf-8")

        return ScriptResult(path=script_path, content=full_content)
