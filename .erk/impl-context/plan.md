# Plan: Objective #8149, Node 1.1 — Establish Scenario Format, Directory Structure, and Template

Part of Objective #8149, Node 1.1

## Context

Erk's test infrastructure has 5 layers of automated tests (fakes, real gateway, integration, CLI commands, core logic) but no way to verify end-to-end CLI workflows against real GitHub infrastructure. Objective #8149 introduces markdown-driven manual test scenarios — step-by-step runbooks executed by a human against a real GitHub repo. Node 1.1 establishes the foundational format, directory structure, and template that all subsequent scenarios will follow.

This is a **documentation-only deliverable** — no Python code changes needed.

## Deliverables

### 1. Create `tests/scenarios/` directory

Flat structure for now — subdirectories will be created in Phase 2 when scenarios are added per category. No `__init__.py` needed (not a Python package, won't interfere with pytest).

```
tests/scenarios/
  README.md
  template.md
```

### 2. Create `tests/scenarios/README.md`

Explains the scenario system (~100 lines). Sections:
- **What are scenarios** — manual CLI test runbooks for real-infrastructure verification (Layer 5+)
- **When to use** — verifying workflows end-to-end against a real GitHub repo
- **How to run** — prerequisites, then follow scenario steps in order
- **Format quick reference** — frontmatter fields, section structure, variable binding, step format
- **Conventions** — kebab-case filenames, one scenario per workflow, self-contained with cleanup
- **Relationship to existing tests** — complements the 5-layer fake-driven architecture

### 3. Create `tests/scenarios/template.md`

Copyable template defining the canonical format:

**Frontmatter fields:**

| Field | Required | Purpose |
|-------|----------|---------|
| `title` | Yes | Human-readable scenario name |
| `workflow` | Yes | Category (e.g., `objective-lifecycle`, `plan-workflow`, `pr-operations`) |
| `commands` | Yes | List of erk CLI commands exercised |
| `prerequisites` | No | What must be true before running |
| `estimated_duration` | No | Approximate human execution time |

**Body sections (4 sections):**

1. **Variables** — table of `$VAR` names and descriptions
2. **Setup** — numbered steps to create prerequisite state
3. **Steps** — numbered test steps with commands and expected outcomes
4. **Cleanup** — numbered steps to tear down created resources

**Step format convention:**

```markdown
### 1. Step description

Run:

```bash
erk command $VAR
```

Capture [the value] **as $VAR_NAME**.

**Expected:** Command exits 0. Output includes relevant detail.
```

**Variable binding:** `$UPPER_SNAKE` syntax, bound with "**as $VAR**" after command blocks. Human extracts value from output.

### 4. Create `docs/learned/testing/scenario-format.md`

Agent-discoverable format reference with proper frontmatter:

```yaml
---
title: Manual CLI Test Scenario Format
read_when:
  - "writing manual CLI test scenarios"
  - "adding scenarios to tests/scenarios/"
  - "understanding the scenario markdown format"
tripwires:
  - action: "creating a scenario without YAML frontmatter"
    warning: "All scenarios require frontmatter with title, workflow, and commands. Copy from tests/scenarios/template.md."
  - action: "creating a scenario that depends on state from another scenario"
    warning: "Scenarios must be self-contained. Each handles its own setup and cleanup."
last_audited: "2026-02-25 00:00 PT"
audit_result: clean
---
```

Documents: frontmatter schema, body structure, step format, variable binding, naming conventions, anti-patterns.

### 5. Update `tests/AGENTS.md`

Add after the "Other Test Directories" section (~5 lines):

```markdown
### Manual CLI Test Scenarios

- `tests/scenarios/` — Markdown-driven manual test runbooks for real-infrastructure verification
- NOT Python test files — human-readable step-by-step procedures
- See [tests/scenarios/README.md](scenarios/README.md) for format and usage
```

### 6. Run `erk docs sync`

Regenerate index and tripwire files after creating the learned doc.

## Key Files

- `tests/scenarios/README.md` — **new** — scenario system overview
- `tests/scenarios/template.md` — **new** — copyable scenario template
- `docs/learned/testing/scenario-format.md` — **new** — agent-discoverable format reference
- `tests/AGENTS.md` — **edit** — add scenarios reference

## Design Decisions

- **No subdirectories yet** — create them in Phase 2 when scenarios are added; avoids speculative structure before Node 1.3 validates the format
- **No `__init__.py`** — scenarios are markdown, not Python; no pytest discovery interference
- **Minimal frontmatter** — 5 fields (2 optional); don't over-engineer before validation
- **Four body sections** — maps to arrange/act/assert/teardown; empty sections get "Not needed" note
- **`estimated_duration` is allowed** — this is human execution time for the scenario, not implementation effort (which is what the "no time estimates" rule prohibits)

## Verification

1. Confirm `tests/scenarios/README.md` and `template.md` render correctly as plain markdown
2. Run `erk docs sync` and verify `docs/learned/testing/scenario-format.md` appears in the index
3. Run `make docs-check` to validate generated files
4. Run `prettier --check tests/scenarios/` to confirm formatting
5. Visually confirm `tests/AGENTS.md` correctly links to the new scenarios section
