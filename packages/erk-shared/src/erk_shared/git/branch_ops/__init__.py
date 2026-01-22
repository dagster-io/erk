"""Git branch operations sub-gateway.

This module provides a separate gateway for branch mutation operations,
allowing BranchManager to be the enforced abstraction for branch mutations
while keeping query operations on the main Git gateway.

Import from submodules:
- abc: GitBranchOps
- real: RealGitBranchOps
- fake: FakeGitBranchOps
- dry_run: DryRunGitBranchOps
- printing: PrintingGitBranchOps
"""
