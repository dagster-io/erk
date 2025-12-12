"""Unified PR submission integration.

This module provides a two-layer PR submission architecture:
1. Core layer: Always runs - git push + gh pr create (works without Graphite)
2. Graphite layer: Optional - adds stack metadata via gt submit

The core layer handles:
- Auth checks (gh auth)
- Uncommitted changes detection/commit
- Issue linking (reads .impl/issue.json)
- git push -u origin <branch>
- gh pr create (or update existing)
- PR footer with checkout instructions

The Graphite layer (optional) handles:
- Graphite auth check
- gt submit (adds stack metadata to existing PR)
"""
