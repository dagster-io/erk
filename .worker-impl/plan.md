# Plan: Split test_init.py into Subpackage

## Goal
Convert `tests/commands/setup/test_init.py` (1833 lines, ~55 tests) into a subpackage with logically grouped test files.

## Proposed Structure

```
tests/commands/setup/init/
├── __init__.py
├── test_global_config.py     # 4 tests - global config creation, graphite detection
├── test_presets.py           # 6 tests - preset auto-detection and explicit selection
├── test_project_setup.py     # 8 tests - config location, force, stepped flow, git repo
├── test_gitignore.py         # 5 tests - gitignore entry handling
├── test_shell.py             # 14 tests - shell detection, completion, confirmation
├── test_claude_permissions.py # 5 tests - Claude permission prompts
├── test_hooks.py             # 8 tests - hooks flag, artifact sync
└── test_statusline.py        # 6 tests - statusline setup
```

## File Contents

### test_global_config.py (4 tests)
- `test_init_creates_global_config_first_time`
- `test_init_prompts_for_erk_root`
- `test_init_detects_graphite_installed`
- `test_init_detects_graphite_not_installed`

### test_presets.py (6 tests)
- `test_init_auto_preset_detects_dagster`
- `test_init_auto_preset_uses_generic_fallback`
- `test_init_explicit_preset_dagster`
- `test_init_explicit_preset_generic`
- `test_init_list_presets_displays_available`
- `test_init_invalid_preset_fails`

### test_project_setup.py (8 tests)
- `test_init_creates_config_at_erk_dir`
- `test_init_force_overwrites_existing_config`
- `test_init_skips_silently_when_already_erkified`
- `test_init_not_in_git_repo_fails`
- `test_init_stepped_flow_shows_three_steps`
- `test_init_skips_project_setup_when_already_erkified`
- `test_init_force_overwrites_when_already_erkified`
- `test_init_step1_shows_repo_name`

### test_gitignore.py (5 tests)
- `test_init_adds_env_to_gitignore`
- `test_init_skips_gitignore_entries_if_declined`
- `test_init_adds_erk_scratch_and_impl_to_gitignore`
- `test_init_handles_missing_gitignore`
- `test_init_preserves_gitignore_formatting`

### test_shell.py (14 tests)
- `test_init_first_time_offers_shell_setup`
- `test_init_shell_flag_only_setup`
- `test_init_detects_bash_shell`
- `test_init_detects_zsh_shell`
- `test_init_detects_fish_shell`
- `test_init_skips_unknown_shell`
- `test_init_prints_completion_instructions`
- `test_init_prints_wrapper_instructions`
- `test_init_skips_shell_if_declined`
- `test_shell_setup_confirmation_declined_with_shell_flag`
- `test_shell_setup_confirmation_accepted_with_shell_flag`
- `test_shell_setup_confirmation_declined_first_init`
- `test_shell_setup_permission_error_with_shell_flag`
- `test_shell_setup_permission_error_first_init`

### test_claude_permissions.py (5 tests)
- `test_init_offers_claude_permission_when_missing`
- `test_init_skips_claude_permission_when_already_configured`
- `test_init_skips_claude_permission_when_no_settings`
- `test_init_handles_declined_claude_permission`
- `test_init_handles_declined_write_confirmation`

### test_hooks.py (8 tests)
- `test_init_hooks_flag_adds_hooks_to_empty_settings`
- `test_init_hooks_flag_skips_when_already_configured`
- `test_init_hooks_flag_handles_declined`
- `test_init_hooks_flag_creates_settings_if_missing`
- `test_init_hooks_flag_only_does_hook_setup`
- `test_init_main_flow_syncs_hooks_automatically`
- `test_init_syncs_artifacts_successfully`
- `test_init_shows_warning_on_artifact_sync_failure`

### test_statusline.py (6 tests)
- `test_statusline_setup_configures_empty_settings`
- `test_statusline_setup_creates_settings_if_missing`
- `test_statusline_setup_skips_when_already_configured`
- `test_statusline_setup_prompts_for_different_command`
- `test_statusline_setup_replaces_when_confirmed`
- `test_init_statusline_flag_recognized`

## Implementation Steps

1. Create `tests/commands/setup/init/` directory
2. Create `__init__.py` in the new directory
3. Create each test file with:
   - The docstring from original file (mock usage policy)
   - Shared imports (will vary per file based on needs)
   - The relevant test functions
4. Delete the original `test_init.py`
5. Run tests to verify: `uv run pytest tests/commands/setup/init/ -v`

## Shared Imports Pattern

Each file will need a subset of these imports:
```python
import json
import os
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.init import perform_statusline_setup
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_isolated_fs_env
```

## Notes
- Mock usage policy docstring should go in each file that uses mocks
- Each file should only import what it needs
- `__init__.py` can be empty (just needs to exist for package recognition)