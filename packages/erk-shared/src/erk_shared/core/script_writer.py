"""Shell activation script writing abstraction - ABC and types.

This module provides ScriptResult and the abstract ScriptWriter interface.
The real implementation (RealScriptWriter) remains in erk.core.script_writer.

ScriptResult is a self-documenting return type for commands that generate shell
activation scripts. The key insight is that ScriptResult knows how to output
itself correctly to the right stream (stdout vs stderr), preventing an entire
class of shell integration bugs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


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
