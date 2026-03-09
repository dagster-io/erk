# Spike: Validate vercel-labs/skills CLI as erk skill install backend

## Context

Erk currently maintains its own multi-backend skill installation code (`codex_portable.py`, `backend_agent_dir()`, wheel bundling via pyproject.toml). The vercel-labs/skills CLI (`npx skills`) already handles 40+ agent backends, uses the same SKILL.md format erk uses, and discovers skills in `.claude/skills/*/SKILL.md` — erk's exact layout.

This spike validates that the skills CLI can discover and install erk skills from the erk repo before committing to a full architectural integration. No changes to `erk init` or the capability system.

**Decision context:**
- Source: erk repo itself (not a separate repo)
- Fallback: None — Node.js will be a hard requirement (no wheel-copy fallback)
- Scope: POC only — gateway + manual validation

## Step 1: Manual validation

Run these commands from a scratch directory to validate the skills CLI works with erk's layout:

```bash
# 1. List available skills from local erk repo
npx skills add /Users/schrockn/code/erk --list

# 2. Install a single skill to a test project
mkdir /tmp/erk-skills-spike && cd /tmp/erk-skills-spike
git init
npx skills add /Users/schrockn/code/erk --skill dignified-python -a claude-code -y

# 3. Verify the installed skill matches source
diff -r .claude/skills/dignified-python /Users/schrockn/code/erk/.claude/skills/dignified-python

# 4. Test GitHub remote path (validates distribution story)
npx skills add schrockn/erk --skill dignified-python -a claude-code -y --list

# 5. Test multiple skills at once
npx skills add /Users/schrockn/code/erk --skill dignified-python --skill fake-driven-testing -a claude-code -y
```

**What to observe:**
- Does `--list` show all 11 bundled + 11 unbundled skills from `.claude/skills/`?
- Are SKILL.md frontmatter `name` and `description` parsed correctly?
- Does the installed directory match the source exactly?
- Does `skills-lock.json` get created with correct entries?
- Does `.agents/skills/` canonical directory get created (symlink mode)?

## Step 2: Create SkillsCli gateway

Minimal 3-file gateway following erk's established pattern.

### `packages/erk-shared/src/erk_shared/gateway/skills_cli/__init__.py`
Empty.

### `packages/erk-shared/src/erk_shared/gateway/skills_cli/types.py`
```python
@dataclass(frozen=True)
class SkillsCliResult:
    success: bool
    exit_code: int
    message: str
```

### `packages/erk-shared/src/erk_shared/gateway/skills_cli/abc.py`
```python
class SkillsCli(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def list_skills(self, *, source: str) -> SkillsCliResult: ...

    @abstractmethod
    def add_skills(
        self, *, source: str, skill_names: list[str], agents: list[str]
    ) -> SkillsCliResult: ...

    @abstractmethod
    def remove_skills(
        self, *, skill_names: list[str], agents: list[str]
    ) -> SkillsCliResult: ...
```

### `packages/erk-shared/src/erk_shared/gateway/skills_cli/real.py`
- `is_available()`: checks `shutil.which("npx")` is not None
- `add_skills()`: runs `npx skills add {source} --skill {name} -a {agents} -y --no-telemetry`
- `remove_skills()`: runs `npx skills remove --skill {name} -a {agents} -y`
- `list_skills()`: runs `npx skills add {source} --list` (the list flag is on `add`, not a separate command)
- All use `run_subprocess_with_context()` from erk_shared

### `packages/erk-shared/src/erk_shared/gateway/skills_cli/fake.py`
```python
class FakeSkillsCli(SkillsCli):
    def __init__(self, *, available: bool):
        self._available = available
        self._add_calls: list[...] = []
        self._remove_calls: list[...] = []
    # Records calls for assertion in tests
```

### Key references to follow:
- Gateway pattern: `packages/erk-shared/src/erk_shared/gateway/shell/` (3-file example)
- Subprocess wrapper: `packages/erk-shared/src/erk_shared/subprocess_utils.py` (`run_subprocess_with_context`)
- ABC conventions: `docs/learned/architecture/gateway-abc-implementation.md`

## Step 3: Wire into ErkContext

- Add `skills_cli: SkillsCli` field to `ErkContext` in `packages/erk-shared/src/erk_shared/context/context.py`
- Production: `RealSkillsCli()`
- Test: `FakeSkillsCli(available=True)` in `ErkContext.for_test()`

## Step 4: Write a basic test

One test file: `tests/unit/gateway/test_skills_cli.py`

- Test `FakeSkillsCli` records calls correctly
- Test `RealSkillsCli.is_available()` (unit, checks shutil.which)
- Integration test (marked `@pytest.mark.integration`): actually run `npx skills add` against local erk repo in a temp directory, verify files appear

## Verification

1. Run manual validation commands from Step 1, confirm skills install correctly
2. Run `make fast-ci` — gateway + test pass, no regressions
3. From a temp directory, verify `npx skills add /path/to/erk --list` shows erk skills
4. Verify `npx skills add /path/to/erk --skill dignified-python -a claude-code -y` installs to `.claude/skills/dignified-python/`

## Out of scope (future work)

- Integrating into `erk init` / `erk init capability add`
- Removing `codex_portable.py`, `backend_agent_dir()`, wheel bundling
- State migration from `.erk/state.toml` to `skills-lock.json`
- Removing `backend` parameter from capability interfaces
