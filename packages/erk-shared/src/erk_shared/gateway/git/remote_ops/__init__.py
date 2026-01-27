"""Git remote operations sub-gateway.

This module provides a separate gateway for remote operations,
including fetch, pull, push, and remote URL queries.

Import from submodules:
- abc: GitRemoteOps
- real: RealGitRemoteOps
- fake: FakeGitRemoteOps
- dry_run: DryRunGitRemoteOps
- printing: PrintingGitRemoteOps
"""
