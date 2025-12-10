"""Shell completion script generation operations.

This module provides abstraction over completion script generation for different
shells (bash, zsh, fish). This abstraction enables dependency injection for testing
without mock.patch.
"""

from abc import ABC, abstractmethod


class Completion(ABC):
    """Abstract interface for shell completion script generation.

    This abstraction enables testing without mock.patch by making completion
    operations injectable dependencies.
    """

    @abstractmethod
    def generate_bash(self) -> str:
        """Generate bash completion script.

        Returns:
            Bash completion script as a string.

        Example:
            >>> completion_ops = RealCompletion()
            >>> script = completion_ops.generate_bash()
            >>> print(script)  # Bash completion code
        """
        ...

    @abstractmethod
    def generate_zsh(self) -> str:
        """Generate zsh completion script.

        Returns:
            Zsh completion script as a string.

        Example:
            >>> completion_ops = RealCompletion()
            >>> script = completion_ops.generate_zsh()
            >>> print(script)  # Zsh completion code
        """
        ...

    @abstractmethod
    def generate_fish(self) -> str:
        """Generate fish completion script.

        Returns:
            Fish completion script as a string.

        Example:
            >>> completion_ops = RealCompletion()
            >>> script = completion_ops.generate_fish()
            >>> print(script)  # Fish completion code
        """
        ...

    @abstractmethod
    def get_erk_path(self) -> str:
        """Get path to erk executable.

        Returns:
            Absolute path to erk executable.

        Example:
            >>> completion_ops = RealCompletion()
            >>> path = completion_ops.get_erk_path()
            >>> print(path)  # e.g., "/usr/local/bin/erk"
        """
        ...
