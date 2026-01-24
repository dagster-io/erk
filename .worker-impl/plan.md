# Consolidated Documentation Plan: erk-learn Plans

> **Consolidates:** #5842, #5841, #5839, #5836, #5835, #5828, #5822, #5819, #5808, #5813

## Source Plans

| Issue | Title | Status |
|-------|-------|--------|
| #5842 | Emoji Category Prefixes for Command Palette | Documentation needed |
| #5841 | Strip "Documentation Plan:" Prefix from Learn Plan Titles | Mostly implemented |
| #5839 | Fix sync-divergence command documentation | Implemented, optional tripwire |
| #5836 | Add Workflow Run Backlink to Plans | Feature complete, needs docs |
| #5835 | Enhanced PR Comment for erk pr address-remote | Feature complete, needs docs |
| #5828 | Add Plan Context Phase to erk pr submit | Feature complete, needs docs |
| #5822 | Add streaming flags to pr-address.yml | Feature complete, partial docs |
| #5819 | Add erk pr address-remote command | Feature complete, needs docs |
| #5808 | Update PR Title for No-Changes Scenario | Mostly implemented |
| #5813 | Document erk-learn documentation improvements | Tripwires implemented |

## Investigation Findings

### Already Implemented (Skip)

1. **#5841 prefix stripping** - `_PLAN_PREFIXES` tuple already includes "Documentation Plan: " (verified in code)
2. **#5813 tripwires** - All 4 tripwires added (function signature atomicity, import path refactoring, fake gateway attributes, pycache collisions)
3. **#5839 sync-divergence** - Command documentation already fixed in commit 9510f9c4
4. **#5808 no-changes PR title** - `[no-changes]` prefix and `_build_no_changes_title()` function implemented

### Features Implemented But Undocumented

1. **Workflow run backlink** (commit b94f43a17) - `created_from_workflow_run_url` field exists in code but not documented
2. **PR address-remote command** (commit 76e89beef) - CLI command exists but no docs
3. **Plan context phase** (commit 7a5a776da) - Phase 3 added to PR submit but not documented
4. **Streaming flags for pr-address** (commit 7c477a356) - Workflow aligned but no dedicated docs

### Documentation Gaps (Needs Work)

1. **TUI Command Palette** - CommandCategory enum, CATEGORY_EMOJI mapping, get_display_name pattern not documented
2. **Metadata Field Workflow** - No process doc for adding new plan metadata fields
3. **PR Submit Phases** - No dedicated phases documentation
4. **Workflow Flag Consistency Matrix** - No cross-workflow comparison table

## Remaining Documentation Items

### HIGH Priority

#### 1. TUI Command Category System
**Files:** `docs/learned/tui/command-palette.md`, `docs/learned/tui/adding-commands.md`
**From:** #5842

Add sections documenting:
- `CommandCategory` enum (ACTION, OPEN, COPY)
- `CATEGORY_EMOJI` mapping (⚡, 🔗, 📋)
- `get_display_name` pattern for dynamic command names
- `Text.assemble()` pattern for emoji + fuzzy highlighting

#### 2. PR Submit Workflow Phases
**File:** `docs/learned/pr-operations/pr-submit-phases.md` (CREATE)
**From:** #5828

Document the 6-phase workflow:
| Phase | Name | Description |
|-------|------|-------------|
| 1 | Analyzing changes | Collect diff and commit info |
| 2 | Collecting metadata | Gather branch/repo context |
| 3 | Fetching plan context | Extract plan from linked issue |
| 4 | Generating PR | AI creates title/description |
| 5 | Graphite enhancement | Add stack metadata if available |
| 6 | Updating PR metadata | Push changes, update GitHub |

#### 3. erk pr address-remote Command
**File:** `.claude/commands/erk/pr-address-remote.md` (CREATE or UPDATE)
**From:** #5819, #5835

Document:
- Command syntax: `erk pr address-remote <PR_NUMBER> [--model MODEL]`
- Local vs remote addressing decision matrix
- Plan dispatch metadata tracking for P{issue} branches
- When to use remote vs local `/erk:pr-address`

#### 4. Workflow Run Backlink Metadata
**File:** `docs/learned/planning/learn-plan-metadata-fields.md` (UPDATE)
**From:** #5836

Add `created_from_workflow_run_url` field documentation:
- Type: `string` (nullable)
- When populated: During learn-dispatch.yml execution
- URL construction: `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}`

### MEDIUM Priority

#### 5. Workflow Flag Consistency Matrix
**File:** `docs/learned/ci/github-actions-claude-integration.md` (UPDATE)
**From:** #5822

Add comparison table:
| Workflow | --print | --verbose | --output-format | --dangerously-skip-permissions |
|----------|---------|-----------|-----------------|--------------------------------|
| erk-impl.yml | Yes | Yes | stream-json | Yes |
| learn-dispatch.yml | Yes | Yes | stream-json | Yes |
| pr-address.yml | Yes | Yes | stream-json | Yes |

#### 6. Metadata Field Addition Workflow
**File:** `docs/learned/planning/metadata-field-workflow.md` (CREATE)
**From:** #5836

5-file coordination checklist:
1. `schemas.py` - Add field to PlanHeaderFieldName, optional_fields
2. `plan_header.py` - Add parameter to creation functions
3. `plan_issues.py` - Thread parameter through
4. `plan_save_to_issue.py` - Add CLI option
5. Test fixtures - Update with new field

### LOW Priority

#### 7. Optional Tripwire: gt restack Misapplication
**File:** `docs/learned/architecture/git-graphite-quirks.md` (UPDATE frontmatter)
**From:** #5839

```yaml
tripwires:
  - action: "using `gt restack` to resolve branch divergence errors"
    warning: "gt restack only handles parent-child stack rebasing, NOT same-branch remote divergence. Use git rebase origin/$BRANCH first."
```

#### 8. Local vs Remote PR Addressing Guide
**File:** `docs/learned/erk/pr-address-workflows.md` (CREATE)
**From:** #5819, #5835

Decision matrix comparing:
- Branch checkout requirement
- Interactive confirmation
- Error recovery
- Plan metadata tracking

## Files to Modify/Create

| Action | Path |
|--------|------|
| UPDATE | `docs/learned/tui/command-palette.md` |
| UPDATE | `docs/learned/tui/adding-commands.md` |
| CREATE | `docs/learned/pr-operations/pr-submit-phases.md` |
| UPDATE | `docs/learned/planning/learn-plan-metadata-fields.md` |
| UPDATE | `docs/learned/ci/github-actions-claude-integration.md` |
| CREATE | `docs/learned/planning/metadata-field-workflow.md` |
| UPDATE | `docs/learned/architecture/git-graphite-quirks.md` (frontmatter) |
| CREATE | `docs/learned/erk/pr-address-workflows.md` |

## Verification

1. Run `erk docs sync` after updating frontmatter to regenerate tripwires.md
2. Verify all new docs appear in `docs/learned/index.md`
3. Run `make format` to ensure markdown formatting
4. Check that links between documents work

## Attribution

Items by source plan:
- **#5842**: Items 1 (TUI categories)
- **#5828**: Items 2 (PR submit phases)
- **#5819, #5835**: Items 3, 8 (PR address-remote)
- **#5836**: Items 4, 6 (workflow backlink, metadata workflow)
- **#5822**: Items 5 (workflow flags)
- **#5839**: Items 7 (gt restack tripwire)
- **#5841, #5808, #5813**: Already implemented (skip)