"""Git tag operations sub-gateway.

This module provides a separate gateway for tag operations,
including checking tag existence, creating tags, and pushing tags.

Import from submodules:
- abc: GitTagOps
- real: RealGitTagOps
- fake: FakeGitTagOps
- dry_run: DryRunGitTagOps
- printing: PrintingGitTagOps
"""
