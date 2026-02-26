# Documentation Plan: Fix modal dismiss keys (Esc/q/Space) not working

## Context

This PR (#8309) fixes an inverted logic bug introduced in PR #8299. That earlier PR added `on_key()` handlers to three modal screens to prevent keystroke leakage to the underlying view, but the dismiss logic was backwards: instead of dismissing on Esc/q/Space, the modals dismissed on every *other* key, making the expected dismiss keys non-functional. The fix was simple — changing `not in` to `in` in three files — but the underlying pattern is subtle and easy to get wrong again.

Documentation matters here because Textual's event propagation model is non-obvious: when `on_key()` calls both `event.prevent_default()` and `event.stop()`, BINDINGS never fire. The handler must explicitly implement all desired behavior, including dismiss keys. This is counterintuitive — the code reads backwards when you write `if event.key in (dismiss_keys): self.dismiss()` combined with unconditional event consumption. Future agents will encounter this pattern when fixing keystroke leakage or implementing modal screens, and without documentation, they're likely to make the same mistake.

The implementation session demonstrated excellent plan-following: the agent completed the fix in under 10 turns with zero deviations, properly verified a pre-existing test failure wasn't caused by the changes, and auto-fixed unrelated Prettier violations. This efficiency was enabled by a high-quality plan with exact line numbers and before/after code snippets. The testing pattern (stash, verify on base branch, restore) and the Prettier auto-fix distinction (`make prettier` vs `make prettier-check`) are also worth documenting.

## Raw Materials

PR #8309

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 9 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score >= 4) | 2 |
| Potential tripwires (score 2-3) | 0 |

## Documentation Items

### HIGH Priority

#### 1. Inverted Logic Trap in Modal Dismiss Keys

**Location:** `docs/learned/tui/modal-screen-pattern.md` (tripwire frontmatter)
**Action:** UPDATE
**Source:** [Impl], [PR #8309]

**Draft Content:**

```markdown
# Add to tripwires frontmatter in docs/learned/tui/modal-screen-pattern.md:

tripwires:
  - action: "implementing on_key() handler with 'if event.key not in (...)' before dismiss()"
    warning: "INVERTED LOGIC: Use 'if event.key in (...)' to dismiss on specific keys. The 'not in' pattern dismisses on every OTHER key when combined with unconditional prevent_default() + stop(). See section 'Keystroke Leakage Prevention'."
```

This is the primary tripwire from this implementation. The inverted logic pattern appeared in three separate files, suggesting copy-paste without verification. Score 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2).

---

#### 2. Event Consumption Blocks BINDINGS

**Location:** `docs/learned/textual/quirks.md` (tripwire frontmatter)
**Action:** UPDATE
**Source:** [Impl], [PR #8309]

**Draft Content:**

```markdown
# Add to tripwires frontmatter in docs/learned/textual/quirks.md:

tripwires:
  - action: "calling event.prevent_default() + event.stop() in on_key() without implementing dismiss logic"
    warning: "This blocks BINDINGS from firing. You must explicitly call dismiss() for keys that should close the modal."
```

Score 4/10 (Non-obvious +2, External tool quirk +1, Cross-cutting +1). This tripwire captures the root cause: when you consume all events, you must manually implement what BINDINGS would have done.

---

#### 3. Modal Keystroke Isolation Pattern — New Section

**Location:** `docs/learned/tui/modal-screen-pattern.md`
**Action:** UPDATE (add new section after "3. BINDINGS for Navigation")
**Source:** [Impl], [PR #8309]

**Draft Content:**

```markdown
### 4. Keystroke Leakage Prevention

When a modal screen needs to prevent unmapped keystrokes from leaking to the underlying view (e.g., pressing "s" in a modal triggering sort mode on the main screen), use the `on_key()` override pattern.

**When to use:**
- Use BINDINGS alone when unmapped keys can safely pass through
- Add `on_key()` when you need to consume ALL keys to prevent leakage

**The pattern:**

<!-- Source: src/erk/tui/screens/help_screen.py, HelpScreen.on_key -->

See `HelpScreen.on_key()` in `src/erk/tui/screens/help_screen.py` for the canonical implementation. The handler:

1. Calls `event.prevent_default()` — prevents Textual from calling base class handlers and BINDINGS
2. Calls `event.stop()` — prevents event from bubbling to parent widgets
3. Checks `if event.key in (dismiss_keys)` — explicitly dismisses on allowed keys

**Critical: The condition must use `in`, not `not in`.** When you unconditionally consume events, the condition checks which keys SHOULD trigger dismissal, not which keys to ignore.

**Three modal patterns in erk:**
- Pattern A: BINDINGS only — `PlanDetailScreen`, `UnresolvedCommentsScreen`
- Pattern B: BINDINGS + on_key() catch-all — `HelpScreen`, `PlanBodyScreen`
- Pattern C: BINDINGS + on_key() with command dispatch — `LaunchScreen`
```

---

#### 4. Fix Stale Reference in Widget Development Doc

**Location:** `docs/learned/textual/widget-development.md` (line 27)
**Action:** UPDATE_REFERENCES
**Source:** [Existing docs check]

**Phantom References:** `IssueBodyScreen` — referenced but not found in codebase

**Cleanup Instructions:**

The document lists `IssueBodyScreen` in the Reference Implementations section, but this screen does not exist in the codebase. Verify if it was renamed (possibly to `PlanBodyScreen` or similar) or deleted. Update the reference to point to an existing screen, or remove the entry if the screen no longer exists. This is a pre-existing issue unrelated to PR #8309.

---

### MEDIUM Priority

#### 5. Key Event Propagation in Textual

**Location:** `docs/learned/textual/quirks.md`
**Action:** UPDATE (expand the "Click Handlers Need Both prevent_default() and stop()" section)
**Source:** [Impl], [PR #8309]

**Draft Content:**

```markdown
### Key Event Propagation in Modal Screens

The same dual-hierarchy model applies to key events. In modal context:

- `event.stop()` → stops bubbling to parent widgets (the underlying view)
- `event.prevent_default()` → stops Textual from calling base class handlers AND prevents BINDINGS from firing

**Critical difference from click handlers:** With key events in modals, `prevent_default()` completely blocks BINDINGS. If your on_key() handler calls both methods unconditionally, you must implement dismiss behavior explicitly — BINDINGS won't fire for escape/q.

<!-- Source: src/erk/tui/screens/help_screen.py, HelpScreen.on_key -->

See `HelpScreen.on_key()` in `src/erk/tui/screens/help_screen.py` for the pattern.

**Cross-reference:** For the full modal keystroke isolation pattern, see [Modal Screen Pattern](../tui/modal-screen-pattern.md).
```

---

#### 6. Pre-existing Test Failure Verification Pattern

**Location:** `docs/learned/testing/testing.md` or new `docs/learned/testing/pre-existing-failure-verification.md`
**Action:** CREATE or UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Pre-existing Test Failure Verification

When encountering unexpected test failures during implementation, verify whether the failure is caused by your changes or pre-existing:

1. **Stash your changes**: `git stash`
2. **Run the failing test on base branch**: Verify it fails without your changes
3. **Restore your changes**: `git stash pop`
4. **Document in PR description**: Note that the failure is pre-existing

This pattern prevents false alarm from blaming your implementation for existing problems. It's especially valuable in large test suites where unrelated failures can cause confusion about whether changes broke something.

**Example from implementation session 870dca6a:** The test `test_execute_palette_command_fix_conflicts_remote_pushes_screen_and_runs_command` failed during CI. The agent properly verified it was pre-existing by stashing changes and confirming the failure on the base branch.
```

---

#### 7. Prettier Auto-Fix vs Check in CI

**Location:** `docs/learned/ci/` (new section in existing ci doc or standalone)
**Action:** CREATE or UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Prettier Auto-Fix in CI Iteration

When running CI iteration workflows:

- **`make prettier`** — auto-fixes formatting issues (modifies files in-place)
- **`make prettier-check`** — reports violations without fixing (exits non-zero if issues found)

In automated CI iteration, prefer `make prettier` to auto-fix formatting issues discovered in unrelated files. This enables the agent to resolve Prettier failures without manual intervention.

**Example:** During implementation of PR #8309, Prettier violations were found in two unrelated documentation files. The agent ran `make prettier` via devrun to auto-fix them, then re-ran CI successfully.
```

---

### LOW Priority

#### 8. Modal Dismiss Testing Checklist

**Location:** `docs/learned/testing/testing.md` or `docs/learned/tui/modal-screen-pattern.md`
**Action:** UPDATE
**Source:** [PR #8309 lessons learned]

**Draft Content:**

```markdown
## Modal Screen Test Checklist

When implementing modal screens, include tests for:

- [ ] Dismiss keys (Esc/q/Space) actually close the modal
- [ ] Unmapped keys don't leak through to underlying view
- [ ] Command keys trigger the expected action
- [ ] BINDINGS are documented correctly (for footer display)

**Why this matters:** The inverted logic bug in PR #8299 survived code review because no tests verified that dismiss keys work. The bug was only caught by manual testing.
```

---

## Stale Documentation Cleanup

### 1. IssueBodyScreen Phantom Reference

**Location:** `docs/learned/textual/widget-development.md` (line 27)
**Action:** UPDATE_REFERENCES
**Phantom References:** `IssueBodyScreen`
**Cleanup Instructions:** The Reference Implementations section lists `IssueBodyScreen` which does not exist in the codebase. Search for similar screen names (PlanBodyScreen, PlanDetailScreen) to determine if it was renamed. Update or remove the reference accordingly.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Inverted Dismiss Key Logic

**What happened:** The original fix for keystroke leakage (PR #8299) used `if event.key not in (dismiss_keys)` before `self.dismiss()`. Combined with unconditional `prevent_default()` + `stop()`, this dismissed the modal on every key EXCEPT the dismiss keys.

**Root cause:** Counterintuitive interaction between event consumption and conditional logic. When you consume all events, the condition checks what SHOULD happen, not what to skip.

**Prevention:** Add tripwire to modal-screen-pattern.md; document the correct pattern with explicit "use `in`, not `not in`" guidance.

**Recommendation:** TRIPWIRE (score 6/10 — implemented as item #1)

### 2. Event Consumption Blocking BINDINGS

**What happened:** The handler called `prevent_default()` expecting BINDINGS to still fire for escape/q keys. They didn't — the handler must implement the dismiss logic itself.

**Root cause:** Misunderstanding of Textual's event propagation model. `prevent_default()` prevents ALL default behavior including BINDINGS.

**Prevention:** Document the interaction in textual/quirks.md; add tripwire for calling both methods without implementing dismiss.

**Recommendation:** TRIPWIRE (score 4/10 — implemented as item #2)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Inverted Logic Trap (not in vs in)

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before implementing on_key() handler with 'if event.key not in (...)' before dismiss()
**Warning:** "INVERTED LOGIC: Use 'if event.key in (...)' to dismiss on specific keys. The 'not in' pattern dismisses on every OTHER key when combined with unconditional prevent_default() + stop()."
**Target doc:** `docs/learned/tui/modal-screen-pattern.md`

This tripwire is essential because the bug pattern is subtle, counterintuitive, and was replicated across three files via copy-paste. Without intervention, future agents fixing keystroke leakage will make the same mistake. The inverted condition reads naturally ("if key is not a dismiss key, then dismiss") but does the opposite of what's intended.

### 2. Event Consumption Blocks BINDINGS

**Score:** 4/10 (Non-obvious +2, Cross-cutting +1, External tool quirk +1)
**Trigger:** Before calling event.prevent_default() + event.stop() in on_key() without implementing dismiss logic
**Warning:** "This blocks BINDINGS from firing. You must explicitly call dismiss() for keys that should close the modal."
**Target doc:** `docs/learned/textual/quirks.md`

This tripwire captures the root cause of the bug. Agents familiar with Textual's BINDINGS system may expect them to work alongside on_key(), but `prevent_default()` blocks all default behavior including BINDINGS. This is documented in Textual but easy to overlook.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Modal Dismiss Testing Gap

**Score:** 3/10 (Specific scope +1, Single occurrence so far +1)
**Notes:** The suggestion to test dismiss key behavior could become tripwire-worthy if this bug pattern recurs. Currently it's LOW priority documentation because the on_key() pattern is less common than BINDINGS-only modals. If additional instances of untested dismiss behavior surface, promote to a testing tripwire.
