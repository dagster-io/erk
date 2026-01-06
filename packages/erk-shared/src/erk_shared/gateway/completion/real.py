"""Real implementation of Completion using subprocess and Click."""

import os
import shutil
import sys

from erk_shared.gateway.completion.abc import Completion
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealCompletion(Completion):
    """Production implementation using subprocess and Click's completion system."""

    def generate_bash(self) -> str:
        """Generate bash completion script via Click's completion system.

        Implementation details:
        - Uses _ERK_COMPLETE=bash_source environment variable
        - Invokes erk executable to generate completion code
        """
        erk_exe = self.get_erk_path()
        env = os.environ.copy()
        env["_ERK_COMPLETE"] = "bash_source"
        result = run_subprocess_with_context(
            cmd=[erk_exe],
            operation_context="generate bash completion script",
            env=env,
        )
        return result.stdout

    def generate_zsh(self) -> str:
        """Generate zsh completion script via Click's completion system.

        Implementation details:
        - Uses _ERK_COMPLETE=zsh_source environment variable
        - Invokes erk executable to generate completion code
        """
        erk_exe = self.get_erk_path()
        env = os.environ.copy()
        env["_ERK_COMPLETE"] = "zsh_source"
        result = run_subprocess_with_context(
            cmd=[erk_exe],
            operation_context="generate zsh completion script",
            env=env,
        )
        return result.stdout

    def generate_fish(self) -> str:
        """Generate fish completion script via Click's completion system.

        Implementation details:
        - Uses _ERK_COMPLETE=fish_source environment variable
        - Invokes erk executable to generate completion code
        """
        erk_exe = self.get_erk_path()
        env = os.environ.copy()
        env["_ERK_COMPLETE"] = "fish_source"
        result = run_subprocess_with_context(
            cmd=[erk_exe],
            operation_context="generate fish completion script",
            env=env,
        )
        return result.stdout

    def get_erk_path(self) -> str:
        """Get erk executable path using shutil.which or sys.argv fallback."""
        erk_exe = shutil.which("erk")
        if not erk_exe:
            # Fallback to current Python + module
            erk_exe = sys.argv[0]
        return erk_exe
