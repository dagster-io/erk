# Plan: Reframe index.md and restructure mkdocs.yml navigation around composability layers

Part of Objective #8384, Node 1.1

## Context

Erk's current docs use a Diataxis-first navigation (Tutorials, Topics, How-To, Reference). This structure is generic and doesn't communicate erk's key differentiator: composability. Users can adopt erk incrementally — start with just the core plan workflow, then add worktree isolation, stacked PRs, remote execution, or multi-plan coordination as needed.

The objective calls for reframing the docs around 5 composability layers:

| Layer | Name | What It Adds |
|-------|------|-------------|
| 0 | Core Workflow | Plan → save → implement → review → land |
| 1 | Worktree Isolation | Parallel agent execution in separate directories |
| 2 | Stacked PRs | Graphite-based dependent PR chains |
| 3 | Remote Execution | GitHub Actions for sandboxed, scalable dispatch |
| 4 | Objectives | Multi-plan coordination toward larger goals |

This node restructures the nav and index.md to make this model the primary organizing principle. Subsequent phases (2-8) will rewrite individual pages to match.

## Changes

### 1. Rewrite `docs/index.md`

**Current:** Generic feature list + Diataxis section listing.

**New structure:**
- Brief intro: what erk is (1-2 sentences)
- **The Composability Model**: table of 5 layers with brief descriptions
- **Getting Started** section: links to prerequisites, installation, first-plan tutorial
- **Layer-by-layer guide**: for each layer, 2-3 sentences explaining what it adds and links to its docs section
- **Other Documentation**: table pointing to docs/learned/, docs/developer/ (for non-user-facing docs)

Tone: position erk as a tool you can adopt incrementally. "Start with Layer 0. Add layers when you need them."

### 2. Restructure `mkdocs.yml` nav

**Current nav** (Diataxis-first):
```
Getting Started → Tutorials → Topics → How-To Guides → Reference → FAQ → Contributing
```

**New nav** (layer-first):
```yaml
nav:
  - Home:
    - index.md
    - TAO.md
  - Getting Started:
    - tutorials/prerequisites.md
    - tutorials/installation.md
    - tutorials/first-plan.md
    - tutorials/advanced-configuration.md
  - The Core Workflow:               # Layer 0
    - topics/the-workflow.md
    - howto/local-workflow.md
    - howto/planless-workflow.md
    - howto/pr-checkout-sync.md
    - howto/conflict-resolution.md
  - Worktrees:                       # Layer 1
    - topics/worktrees.md
    - howto/navigate-branches-worktrees.md
  - Stacked PRs:                     # Layer 2
    - tutorials/graphite-integration.md
  - Remote Execution:                # Layer 3
    - howto/remote-execution.md
    - howto/test-workflows.md
  - Reference:
    - ref/index.md
    - ref/commands.md
    - ref/slash-commands.md
    - ref/configuration.md
    - ref/file-locations.md
  - FAQ:
    - faq/index.md
  - Contributing:
    - contributing/writing-documentation.md
    - howto/documentation-extraction.md
```

**Pages removed from nav** (files kept on disk for later phases to handle):
- `topics/plan-oriented-engineering.md` — skeleton, redundant with TAO.md
- `topics/plan-mode.md` — skeleton, content folded into the-workflow.md (Phase 2)
- `topics/why-github-issues.md` — "premise is false" per objective, deleted in Phase 8
- `topics/index.md`, `tutorials/index.md`, `howto/index.md` — section indexes no longer needed as nav entry points

**Pages relocated:**
- `howto/documentation-extraction.md` → moved under Contributing (better fit)
- `howto/pr-checkout-sync.md`, `howto/conflict-resolution.md` → moved under Core Workflow (PR operations are part of the core cycle)

**Not added (future phases):**
- Layer 4 (Objectives) section — Phase 7 will create `docs/howto/objectives.md` and add the nav section

### 3. No other files modified

Individual page content stays as-is. Phases 2-8 handle rewrites. Cross-references within existing pages that point to removed nav items will still resolve (files stay on disk), but may become stale — that's expected and cleaned up in Phase 8.

## Files Modified

| File | Action |
|------|--------|
| `docs/index.md` | Rewrite |
| `mkdocs.yml` | Restructure nav section |

## Verification

1. Run `mkdocs build` — should succeed with no errors (all referenced files must exist)
2. Run `mkdocs serve` and verify:
   - Home page shows composability layer model
   - Nav sidebar reflects layer-based structure
   - All links in index.md resolve
3. Confirm files removed from nav still exist on disk (for later phases)
