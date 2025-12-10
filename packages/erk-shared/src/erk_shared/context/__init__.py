"""Unified context for erk and dot-agent-kit.

This module provides the canonical ErkContext that holds all dependencies
for erk and dot-agent-kit operations.
"""

from erk_shared.context.context import ErkContext as ErkContext
from erk_shared.context.helpers import get_current_branch as get_current_branch
from erk_shared.context.helpers import require_cwd as require_cwd
from erk_shared.context.helpers import require_git as require_git
from erk_shared.context.helpers import require_github as require_github
from erk_shared.context.helpers import require_issues as require_issues
from erk_shared.context.helpers import require_project_root as require_project_root
from erk_shared.context.helpers import require_prompt_executor as require_prompt_executor
from erk_shared.context.helpers import require_repo_root as require_repo_root
from erk_shared.context.helpers import require_session_store as require_session_store
from erk_shared.context.testing import for_test as for_test
from erk_shared.context.types import GlobalConfig as GlobalConfig
from erk_shared.context.types import LoadedConfig as LoadedConfig
from erk_shared.context.types import NoRepoSentinel as NoRepoSentinel
from erk_shared.context.types import RepoContext as RepoContext
