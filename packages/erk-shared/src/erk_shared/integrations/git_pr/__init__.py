"""Git-only PR workflow operations package.

This package provides the two-phase architecture for git-only PR workflows
(no Graphite required), mirroring the pattern from erk_shared.integrations.gt.

The workflow is:
    Slash Command → Preflight (Python) → AI Analysis (Agent) → Finalize (Python)
"""
