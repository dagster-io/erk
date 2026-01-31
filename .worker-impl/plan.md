# Remove --docker and --codespace flags from implement/prepare

## Summary

Delete the `--docker` and `--codespace` flags from `erk implement` and `erk prepare`, plus all execution code they invoke. Keep the `erk codespace` command group and its gateway abstractions. Also remove CI Docker infrastructure.

## Files to delete entirely

1. `src/erk/cli/commands/docker_executor.py` - Docker execution engine
2. `src/erk/cli/commands/codespace_executor.py` - Codespace execution engine
3. `.erk/docker/Dockerfile` - Local dev Docker image
4. `.github/docker/Dockerfile` - CI Docker image
5. `.github/workflows/build-ci-image.yml` - CI image build workflow
6. `docs/learned/cli/docker-isolation.md` - Docker documentation
7. `tests/unit/cli/commands/test_docker_executor.py` - Docker executor tests
8. `tests/unit/cli/commands/test_codespace_executor.py` - Codespace executor tests

## Files to edit

### 1. `src/erk/cli/commands/implement_shared.py`
- Remove `DEFAULT_DOCKER_IMAGE` constant
- Remove `--docker`, `--codespace`, `--codespace-name`, `--docker-image` options from `implement_common_options` decorator
- Remove docker/codespace validation from `validate_flags()`
- Remove `execute_codespace_mode()` helper function
- Remove any imports of docker_executor or codespace_executor

### 2. `src/erk/cli/commands/implement.py`
- Remove docker/codespace code paths from `_implement_from_issue()`
- Remove docker/codespace code paths from `_implement_from_file()`
- Remove docker/codespace dispatch from `implement()` main function
- Remove imports of docker_executor, codespace_executor, execute_codespace_mode

### 3. `src/erk/cli/commands/prepare.py`
- Remove `--docker`, `--codespace`, `--codespace-name` flags
- Remove any pass-through of these flags to implement

### 4. `tests/unit/cli/commands/test_implement_shared.py`
- Remove any tests related to docker/codespace flag validation

### 5. `tests/commands/implement/test_issue_mode.py` (if it has docker/codespace tests)
- Remove docker/codespace test cases

## Verification

1. `make fast-ci` - all unit tests pass
2. `make all-ci` - full CI passes
3. `erk implement --help` - confirm --docker/--codespace flags are gone
4. `erk prepare --help` - confirm --docker/--codespace flags are gone
5. `erk codespace --help` - confirm codespace subcommands still work