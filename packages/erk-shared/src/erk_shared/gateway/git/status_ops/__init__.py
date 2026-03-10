"""Git status operations sub-gateway.

This module provides a separate gateway for status query operations,
including uncommitted changes detection and merge conflict checking.

Import from submodules:
- abc: GitStatusOps
- real: RealGitStatusOps
- dry_run: DryRunGitStatusOps
"""
