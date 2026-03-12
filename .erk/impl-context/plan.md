# Plan: Tag-Based Capability Display Grouping

## Context

`erk init capability list` shows a flat alphabetical list of ~19 capabilities. Related capabilities (e.g., code-reviews-system + its review definitions) are scattered. Adding a `tag` property enables visual grouping in list output.

Tags are display-only — no dependency enforcement, no filtering. Each capability has at most one tag.

## Tag Assignments

| Tag | Capabilities |
|-----|-------------|
| `code-reviews` | code-reviews-system, review-dignified-code-simplifier, review-dignified-python, review-tripwires |
| `devrun` | devrun-agent, devrun-reminder |
| `dignified-python` | dignified-python, dignified-python-reminder, dignified-code-simplifier |
| `documentation` | learned-docs, explore-docs-reminder, tripwires-reminder |
| `external-tools` | gh, gt |
| None (ungrouped) | erk-planning, fake-driven-testing, erk-bash-permissions, statusline, ruff-format |

## Implementation

### Step 1: Add `tag` property to Capability ABC

**File:** `src/erk/core/capabilities/base.py`

Add a non-abstract `tag` property returning `None` by default (same pattern as `required`, `supported_backends`, `managed_artifacts`).

### Step 2: Set tag on ReviewCapability base class

**File:** `src/erk/core/capabilities/review_capability.py`

Override `tag` to return `"code-reviews"`. All 3 review subclasses inherit it automatically.

### Step 3: Set tags on individual capability classes

Each file gets a `tag` property override:

| File | Tag |
|------|-----|
| `src/erk/capabilities/code_reviews_system.py` | `"code-reviews"` |
| `src/erk/capabilities/agents/devrun.py` | `"devrun"` |
| `src/erk/capabilities/reminders/devrun.py` | `"devrun"` |
| `src/erk/capabilities/reminders/dignified_python.py` | `"dignified-python"` |
| `src/erk/capabilities/reminders/explore_docs.py` | `"documentation"` |
| `src/erk/capabilities/reminders/tripwires.py` | `"documentation"` |
| `src/erk/capabilities/learned_docs.py` | `"documentation"` |

Files that keep `None` (inherit default): `statusline.py`, `erk_bash_permissions.py`, `ruff_format.py`

### Step 4: Add tags to BundledSkillCapability

**File:** `src/erk/capabilities/skills/bundled.py`

- Add `_BUNDLED_SKILL_TAGS` dict mapping skill names to tags:
  - `"dignified-code-simplifier"` → `"dignified-python"`
  - `"gh"` → `"external-tools"`
  - `"gt"` → `"external-tools"`
- Add `_tag: str | None` parameter to `BundledSkillCapability.__init__` (required, no default)
- Add `tag` property returning `self._tag`
- Update `create_bundled_skill_capabilities()` to pass `_tag=_BUNDLED_SKILL_TAGS.get(name)`

### Step 5: Update list command for grouped display

**File:** `src/erk/cli/commands/init/capability/list_cmd.py`

- Add `TAG_DISPLAY_NAMES` dict: `{"code-reviews": "Code Reviews", "devrun": "Devrun", "dignified-python": "Dignified Python", "documentation": "Documentation", "external-tools": "External Tools"}`
- Rewrite `_check_all()` to:
  1. Sort capabilities by `(0 if tagged else 1, tag, name)`
  2. Group by tag using `itertools.groupby`
  3. Render group headers, then capabilities within each group
  4. Ungrouped capabilities go under "Other" at the end
- Extract per-capability rendering into `_render_capability_line()` helper
- Widen name column from 25 to 35 chars for longer names

### Step 6: Update tests

**File:** `tests/unit/cli/commands/init/capability/test_list_cmd.py`

- Update `test_capability_list_sorts_alphabetically` to verify sorting within groups (not globally)
- Add test verifying group headers appear and are in alphabetical order
- Existing content-presence tests (`test_capability_list_shows_available_capabilities`, `test_capability_list_works_without_repo`) should pass unchanged

## Verification

1. Run `uv run pytest tests/unit/cli/commands/init/capability/test_list_cmd.py`
2. Run `erk init capability list` and verify grouped output visually
3. Run `uv run ruff check src/erk/core/capabilities/ src/erk/capabilities/ src/erk/cli/commands/init/capability/`
