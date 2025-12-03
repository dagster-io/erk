"""Parse PR reference from user input.

This module re-exports parse_pr_identifier from the centralized CLI parsing module.
Kept for backwards compatibility with existing imports.
"""

from erk.cli.github_parsing import parse_pr_identifier

# Re-export with explicit assignment per PEP 484 to indicate intentional re-export
parse_pr_reference = parse_pr_identifier
