# Plan: Consolidated Documentation for Draft-PR Backend Rollout

## Context

Sixteen erk-learn plans accumulated from the draft-PR backend rollout (Feb 19-20, 2026). All code is merged. The documentation gap is significant: existing docs contain contradictions and stale content, critical tripwires are missing, and new patterns have no documentation. This plan works through the backlog in priority order, ending with `erk docs sync` to regenerate auto-generated files.

**Critical constraint:** `tripwires.md` files are auto-generated — never edit them directly. Add tripwires to the `tripwires:` frontmatter of source doc files, then run `erk docs sync`.

---

## Phase 1: Fix Contradictions & Stale Content (HIGH)

### Step 1: Fix `visual-status-indicators.md`
**File:** `docs/learned/desktop-dash/visual-status-indicators.md`
- Change "Not yet implemented" (line 22) to reflect: TUI implementation is live (PR #7662)
- Remove reference to unmerged branch `P6564-erk-plan-visual-status-in-02-01-1138`
- Add references to implementation: `lifecycle.py:61-140`, `real.py:639,727-731`
- Update `last_audited` date in frontmatter

### Step 2: Fix `impl-context.md` cleanup section
**File:** `docs/learned/planning/impl-context.md` (lines 33-41)
- Replace `shutil.rmtree()` description with two-phase deferred cleanup pattern:
  - Phase 1: `setup_impl_from_issue.py:202` reads files, does NOT delete
  - Phase 2: `plan-implement.md` Step 2d performs `git rm -rf` + commit + push
- Update "Why It Can Leak" section with new leak vectors
- Add tripwire to frontmatter: "Before removing git-tracked temp directories → defer deletion to git cleanup phase"

### Step 3: Fix `draft-pr-lifecycle.md` format examples
**File:** `docs/learned/planning/draft-pr-lifecycle.md`
- Lines 35, 56: Change `<summary><code>original-plan</code></summary>` → `<summary>original-plan</summary>`
- Lines 101-106: Update backward compat section — new format is plain text, old format had `<code>` tags (still parsed for compatibility)
- Add tripwire: "Before adding `<code>` inside `<summary>` elements → Graphite doesn't render it"

### Step 4: Fix `objective-create.md` typo
**File:** `.claude/commands/erk/objective-create.md` (line 317)
- Change `Title suffix` → `Title prefix`

---

## Phase 2: New Documentation Files (MEDIUM)

All new files need proper frontmatter with `title`, `read_when`, and optionally `tripwires`.

### Step 5: Create `graphite-rendering.md`
**File:** `docs/learned/integrations/graphite-rendering.md`
- Document `<code>` in `<summary>` not rendering in Graphite (only GitHub)
- Document blank-line requirement after `</details>` for proper spacing
- Testing guidance: verify on both github.com AND graphite.dev
- References: `metadata/core.py:61`, `metadata_blocks.py:226`, `draft_pr_lifecycle.py:89-90`
- Include tripwire: "Before adding `<code>` inside `<summary>` → use plain text"

### Step 6: Create `backend-aware-commands.md`
**File:** `docs/learned/tui/backend-aware-commands.md`
- Document backend as third command-filtering dimension (after view mode + data availability)
- `_is_github_backend()` predicate pattern in `registry.py:31-33`
- `CommandContext` with `plan_backend` field (`types.py:23-35`)
- Commands hidden in `draft_pr` mode: `copy_prepare` (shortcut "1"), `copy_prepare_activate` (shortcut "4")
- Include tripwire: "Before adding TUI commands → check all three filter dimensions"

### Step 7: Create `github-review-decision.md`
**File:** `docs/learned/integrations/github-review-decision.md`
- Document GraphQL → `PullRequestInfo` → lifecycle display pipeline
- `reviewDecision` field: `graphql_queries.py:75,148,197`
- `review_decision: str | None` in `types.py:201`
- Values: APPROVED→checkmark, CHANGES_REQUESTED→X, REVIEW_REQUIRED→no indicator
- `format_lifecycle_with_status()` in `lifecycle.py:61-140`

### Step 8: Create `environment-variable-isolation.md`
**File:** `docs/learned/testing/environment-variable-isolation.md`
- Document `ERK_PLAN_BACKEND` contamination pattern (causes 125+ test failures)
- Two `context_for_test()` implementations: `erk-shared` checks env var, local ignores it
- Parameter name difference: `issues` vs `github_issues`
- Mitigation: `monkeypatch.setenv()` or `env_overrides` in test fixtures
- Include tripwire: "Before debugging systematic test failures → check `ERK_PLAN_BACKEND` first"

### Step 9: Create `shell-activation-pattern.md`
**File:** `docs/learned/cli/shell-activation-pattern.md`
- Document `source "$(erk br co <branch> --script)"` pattern
- Why plain `erk br co <branch> && <cmd>` fails (subprocess directory change doesn't persist)
- Implementation: `activation.py`, `activation_config_for_implement()`
- Include tripwire in `docs/learned/cli/` source: "Before generating directory-change commands → use shell activation pattern"

---

## Phase 3: Update Existing Documentation (MEDIUM)

### Step 10: Update `fake-github-mutation-tracking.md`
**File:** `docs/learned/testing/fake-github-mutation-tracking.md`
- Add `_marked_pr_ready` to the tracking list table
- Document three-component pattern: private list, recording method, read-only property with defensive copy

### Step 11: Update `draft-pr-handling.md`
**File:** `docs/learned/pr-operations/draft-pr-handling.md`
- Add section: auto-publishing in `finalize_pr()` (`submit_pipeline.py:687-691`)
- Describe: checks `is_draft`, calls `mark_pr_ready()`, echoes feedback message

### Step 12: Update `view-aware-commands.md`
**File:** `docs/learned/tui/view-aware-commands.md`
- Add section: "Backend as Third Dimension" explaining `plan_backend` filtering
- Cross-reference new `backend-aware-commands.md`

### Step 13: Update `adding-commands.md`
**File:** `docs/learned/tui/adding-commands.md`
- Update provider context section to include `plan_backend` field
- Show wiring in both `MainListCommandProvider` and `PlanCommandProvider`

### Step 14: Update `draft-pr-plan-backend.md`
**File:** `docs/learned/planning/draft-pr-plan-backend.md`
- Add section on title-prefixing behavior (`get_title_tag_from_labels()` in `plan_utils.py:178-190`)
- Add section on GraphQL refactor (`list_plan_prs_with_details()` replacing N+1 REST calls)

### Step 15: Update `plan-backend-migration.md`
**File:** `docs/learned/planning/plan-backend-migration.md`
- Add `add_label()` to the PlanBackend method table (found in `backend.py:398-414`)

---

## Phase 4: Regenerate Auto-Generated Files

### Step 16: Run `erk docs sync`
After all edits, run:
```bash
erk docs sync
```
This regenerates:
- `docs/learned/*/tripwires.md` (from source frontmatter)
- `docs/learned/tripwires-index.md`
- `docs/learned/index.md`

---

## Verification

1. `visual-status-indicators.md` no longer says "Not yet implemented"
2. `impl-context.md` no longer mentions `shutil.rmtree()` in the cleanup section
3. `draft-pr-lifecycle.md` examples use `<summary>original-plan</summary>` (no `<code>` tags)
4. `objective-create.md:317` says "Title prefix"
5. All Phase 2 files exist: `graphite-rendering.md`, `backend-aware-commands.md`, `github-review-decision.md`, `environment-variable-isolation.md`, `shell-activation-pattern.md`
6. `erk docs sync` runs without errors
7. Tripwire counts in category files increase after sync (check with `grep -c "→" docs/learned/*/tripwires.md`)

---

## Files Modified

### Phase 1 (fixes)
- `docs/learned/desktop-dash/visual-status-indicators.md`
- `docs/learned/planning/impl-context.md`
- `docs/learned/planning/draft-pr-lifecycle.md`
- `.claude/commands/erk/objective-create.md`

### Phase 2 (new files)
- `docs/learned/integrations/graphite-rendering.md` (new)
- `docs/learned/tui/backend-aware-commands.md` (new)
- `docs/learned/integrations/github-review-decision.md` (new)
- `docs/learned/testing/environment-variable-isolation.md` (new)
- `docs/learned/cli/shell-activation-pattern.md` (new)

### Phase 3 (updates)
- `docs/learned/testing/fake-github-mutation-tracking.md`
- `docs/learned/pr-operations/draft-pr-handling.md`
- `docs/learned/tui/view-aware-commands.md`
- `docs/learned/tui/adding-commands.md`
- `docs/learned/planning/draft-pr-plan-backend.md`
- `docs/learned/planning/plan-backend-migration.md`
