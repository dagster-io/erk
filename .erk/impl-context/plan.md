# Plan: Create `erk-tui` Skill

## Context

The erk TUI has 44 learned docs (37 in `docs/learned/tui/`, 7 in `docs/learned/textual/`) totaling ~4,265 lines. These raw docs are valuable but hard for agents to navigate — when working on TUI code, agents must grep and read across dozens of files to find relevant patterns.

This plan creates an `erk-tui` skill that distills these raw docs into a curated, task-routed reference. The raw docs remain as living material where new insights land via `/erk:learn`. The skill is the refined layer that agents load for TUI work.

**Flow**: Session insights → `/erk:learn` → `docs/learned/tui/*.md` (raw) → periodic harvest → `.claude/skills/erk-tui/` (curated)

## Deliverables

### 1. Create skill content

**Directory**: `.claude/skills/erk-tui/`

```
.claude/skills/erk-tui/
├── SKILL.md                        # Entry point with routing
└── references/
    ├── architecture.md             # Layers, mixins, directory structure
    ├── data-layer.md               # PlanRowData, PlanFilters, columns, data contract
    ├── commands.md                 # Registration, dual-handler, categories, view-aware
    ├── filtering-and-views.md     # Filter pipeline, toggle, escape chain, view switching
    ├── screens-and-widgets.md     # Modals, tables, status bar, keyboard shortcuts
    ├── async-operations.md        # Streaming, subprocess, multi-op tracking, state snapshots
    └── textual-quirks.md          # Framework gotchas (DataTable, CSS, Rich markup, testing)
```

**SKILL.md structure** (modeled on `fake-driven-testing/SKILL.md`):

```yaml
---
name: erk-tui
description: >
  Erk TUI development patterns for the Textual-based dashboard. Use when adding
  commands, columns, filters, modal screens, or async operations to erk dash.
  Covers architecture, data contracts, command registration, filter pipeline,
  widget lifecycle, streaming output, and Textual framework quirks.
---
```

Body sections:
1. Trigger line and prerequisites (`dignified-python`, `fake-driven-testing`)
2. Architecture overview (condensed layer diagram, data flow, design principles)
3. Quick Decision routing table (task → reference file)
4. Reference index (per-file "Read when" + "Contents")
5. Top ~15 critical tripwires (consolidated from all 44 source docs)
6. Key principles summary (5-6 bullets)

**Content approach**: Distill why/when/checklists from raw docs. Don't copy verbatim — synthesize. Each reference file lists its source docs for harvest traceability.

**Source mapping**:

| Reference | Source docs (from docs/learned/) |
|-----------|--------------------------------|
| architecture.md | tui/architecture, tui/modal-screen-pattern, tui/modal-widget-embedding, tui/runs-tab-architecture |
| data-layer.md | tui/column-addition-pattern, tui/plan-row-data, tui/dashboard-columns, tui/data-contract, tui/derived-display-columns, tui/frozen-dataclass-field-management |
| commands.md | tui/adding-commands, tui/action-inventory, tui/tui-command-registration, tui/dual-handler-pattern, tui/view-aware-commands, tui/command-execution, tui/clipboard-text-generation, tui/command-palette |
| filtering-and-views.md | tui/filter-pipeline, tui/filter-toggle-pattern, tui/view-switching, tui/view-mode-help |
| screens-and-widgets.md | tui/keyboard-shortcuts, tui/status-indicators, tui/lifecycle-display, tui/stacked-pr-indicator, tui/one-shot-prompt-modal, tui/plan-title-rendering-pipeline, tui/title-truncation-edge-cases |
| async-operations.md | tui/streaming-output, tui/subprocess-feedback, tui/multi-operation-tracking, tui/async-action-refresh-pattern, tui/async-state-snapshot, tui/textual-async |
| textual-quirks.md | textual/quirks, textual/background-workers, textual/testing, textual/datatable-markup-escaping, textual/widget-development |

### 2. Register the skill

**File**: `src/erk/capabilities/skills/bundled.py`
- Add `"erk-tui"` to `_UNBUNDLED_SKILLS` frozenset (line 17-32)

No changes needed to `codex_portable.py` or `pyproject.toml` (unbundled skills aren't distributed).

### 3. Update AGENTS.md routing

**File**: `AGENTS.md` line 44-48, add:
```
- **TUI code** → `erk-tui` skill (architecture, commands, data layer, Textual quirks)
```

### 4. Tag raw docs with `curated_in`

Add `curated_in: erk-tui` to the YAML frontmatter of all 40 source docs (excludes auto-generated index.md and tripwires.md files).

The frontmatter validator (`src/erk/agent_docs/operations.py:188`) silently ignores unknown fields — confirmed by reading the code. No schema changes needed. This field is purely a convention for now, enabling future harvest tooling.

**35 files in docs/learned/tui/**:
architecture, adding-commands, action-inventory, async-action-refresh-pattern, async-state-snapshot, clipboard-text-generation, column-addition-pattern, command-execution, command-palette, dashboard-columns, data-contract, derived-display-columns, dual-handler-pattern, filter-pipeline, filter-toggle-pattern, frozen-dataclass-field-management, keyboard-shortcuts, lifecycle-display, modal-screen-pattern, modal-widget-embedding, multi-operation-tracking, one-shot-prompt-modal, plan-row-data, plan-title-rendering-pipeline, runs-tab-architecture, stacked-pr-indicator, status-indicators, streaming-output, subprocess-feedback, textual-async, title-truncation-edge-cases, tui-command-registration, view-aware-commands, view-mode-help, view-switching

**5 files in docs/learned/textual/**:
quirks, background-workers, testing, datatable-markup-escaping, widget-development

### 5. Run `erk docs sync`

After adding `curated_in` frontmatter, run `erk docs sync` to verify no generated files break.

## Implementation Order

1. **Create skill directory and all files** (SKILL.md + 7 references)
2. **Register in bundled.py** (`_UNBUNDLED_SKILLS`)
3. **Update AGENTS.md** routing
4. **Tag 40 raw docs** with `curated_in: erk-tui` frontmatter
5. **Run erk docs sync** to verify
6. **Run tests** to validate

## Verification

1. `uv run pytest tests/unit/artifacts/test_codex_compatibility.py` — validates SKILL.md frontmatter and registration
2. `erk docs sync` — validates frontmatter still parses with `curated_in` field
3. Manual: load skill in Claude Code session, verify decision routing works
4. `grep -r "curated_in: erk-tui" docs/learned/` — confirm all 40 docs tagged

## Key Files

| File | Action |
|------|--------|
| `.claude/skills/erk-tui/SKILL.md` | Create |
| `.claude/skills/erk-tui/references/*.md` (7 files) | Create |
| `src/erk/capabilities/skills/bundled.py` | Edit (add to `_UNBUNDLED_SKILLS`) |
| `AGENTS.md` | Edit (add routing line) |
| `docs/learned/tui/*.md` (35 files) | Edit (add `curated_in` frontmatter) |
| `docs/learned/textual/*.md` (5 files) | Edit (add `curated_in` frontmatter) |
