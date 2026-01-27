"""Git rebase operations sub-gateway.

This module provides a separate gateway for rebase operations,
including rebase onto, continue, abort, and rebase status checking.

Import from submodules:
- abc: GitRebaseOps
- real: RealGitRebaseOps
- fake: FakeGitRebaseOps
- dry_run: DryRunGitRebaseOps
- printing: PrintingGitRebaseOps
"""
