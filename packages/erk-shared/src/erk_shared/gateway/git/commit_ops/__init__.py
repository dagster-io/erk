"""Git commit operations sub-gateway.

This module provides a separate gateway for commit operations,
including staging, committing, amending, and commit message queries.

Import from submodules:
- abc: GitCommitOps
- real: RealGitCommitOps
- fake: FakeGitCommitOps
- dry_run: DryRunGitCommitOps
- printing: PrintingGitCommitOps
"""
