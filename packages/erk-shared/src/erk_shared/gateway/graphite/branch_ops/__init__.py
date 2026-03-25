"""Graphite branch operations sub-gateway.

This module provides a separate gateway for Graphite branch mutation operations,
allowing BranchManager to be the enforced abstraction for branch mutations
while keeping query operations on the main Graphite gateway.

Import from submodules:
- abc: GraphiteBranchOps
- real: RealGraphiteBranchOps
- dry_run: DryRunGraphiteBranchOps
"""
