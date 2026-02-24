# Documentation Plan: Strengthen ternary acceptance in coding standards and remove unused Agent SDK

## Context

This plan addresses documentation learnings from PR #8080, which strengthened ternary operator guidance in coding standards and removed unused Claude Agent SDK code from erkbot. The work was triggered by a false positive from the dignified-code-simplifier review bot, which incorrectly suggested replacing idiomatic Python ternary expressions with `.or_else()` - a method that exists in Rust and Kotlin but not Python.

The implementation revealed several cross-cutting insights about agent behavior: how permissive language in coding standards leads to false positives, how cross-language API contamination can cause hallucinated suggestions, and how coding standards must be coordinated across reviewer and implementation skills. These insights are more valuable than the actual code changes, which are self-documenting within the skill files themselves.

Notably, this plan requires **no new learned documentation files**. All code changes in PR #8080 are self-documenting (skill files ARE documentation, and code removal needs no documentation). However, the sessions revealed three valuable tripwire candidates that will help future agents avoid similar mistakes.

## Raw Materials

See associated session analysis files for full context.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 0     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 3     |

## Documentation Items

### HIGH Priority

**No high-priority documentation items.**

All changes in PR #8080 are self-documenting:
- Skill file updates (`dignified-code-simplifier/SKILL.md` and `dignified-python/dignified-python-core.md`) ARE the documentation
- erkbot code removal requires no documentation since the code was never used

### MEDIUM Priority

**No medium-priority documentation items.**

### LOW Priority

**No low-priority documentation items.**

## Contradiction Resolutions

**No contradictions detected.**

The existing ternary guidance in `.claude/skills/dignified-code-simplifier/SKILL.md` was incomplete but not wrong. The PR strengthened the existing guidance rather than contradicting it.

## Stale Documentation Cleanup

**No stale documentation detected.**

All referenced files in existing documentation are present in the repository. No phantom references found.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Cross-Language API Contamination

**What happened:** The dignified-code-simplifier review bot suggested replacing `main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root` with `.or_else()` pattern.

**Root cause:** Claude's training on multiple programming languages causes "knowledge bleed" where patterns from one language (Rust's `.or_else()`, Kotlin's `?.let`) are suggested for another language (Python) where they don't exist. The suggestion appeared plausible but would have failed at runtime.

**Prevention:** Before suggesting any method, pattern, or API in code, verify it exists in the target language. For Python, check stdlib documentation or search the project codebase. Never suggest language-specific patterns from other languages without explicit verification.

**Recommendation:** TRIPWIRE - This is a HIGH severity cross-cutting concern that affects any code suggestion scenario. Score 6/10.

### 2. Permissive Language in Coding Standards

**What happened:** The dignified-code-simplifier skill stated "Simple single-level ternaries are idiomatic and acceptable" but this wasn't emphatic enough to prevent the false positive.

**Root cause:** Review bots and simplification agents have a bias toward suggesting improvements. Permissive language ("X is acceptable", "X is okay") is interpreted as "tolerated but not preferred" rather than "leave this alone."

**Prevention:** Use prohibitive language ("NEVER flag X", "DO NOT suggest Y") in coding standards when you want agents to leave code alone. Permissive language invites optimization attempts.

**Recommendation:** TRIPWIRE - This affects accuracy of all automated reviews. Score 5/10.

### 3. Skill Coordination Gap

**What happened:** When strengthening ternary guidance, updates were needed in two locations: `dignified-code-simplifier` (for review) and `dignified-python-core` (for implementation).

**Root cause:** Coding standards exist in two parallel forms - one for reviewing/refactoring existing code and one for writing new code. Without coordinated updates, agents apply different standards depending on context.

**Prevention:** When editing coding standard skills in `.claude/skills/dignified-*`, check if updates are needed in BOTH dignified-code-simplifier (reviewer) and dignified-python-core (implementation standards).

**Recommendation:** TRIPWIRE - This causes inconsistent agent behavior across contexts. Score 4/10.

### 4. Pre-Existing CI Failure Handling

**What happened:** Implementation session encountered CI failure for missing `pyproject.toml` in `erk-slack-bot` directory (from recent package rename).

**Root cause:** Workspace members must have `pyproject.toml` files. The package rename left orphaned workspace configuration.

**Prevention:** Agent correctly identified this as pre-existing and unrelated to current changes by checking git history. This demonstrates good engineering judgment: verify whether CI failures are caused by current changes (must fix), pre-existing and related (may need to fix), or pre-existing and unrelated (document and proceed).

**Recommendation:** CONTEXT_ONLY - This is good agent behavior worth noting but doesn't warrant a tripwire.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Cross-Language API Contamination

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before suggesting a method, pattern, or API in Python code

**Warning:** Verify the method exists in Python stdlib or the project's codebase. DO NOT suggest patterns from other languages like Rust's `.or_else()` or Kotlin's `?.let` - these do not exist in Python.

**Target doc:** `docs/learned/universal-tripwires.md`

This is tripwire-worthy because the failure mode is silent and plausible - the suggestion looks reasonable to anyone unfamiliar with Rust/Kotlin, and the error only surfaces when someone tries to implement it. The harm is wasted time investigating phantom APIs and loss of trust in automated suggestions.

### 2. Permissive vs Prohibitive Language in Standards

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)

**Trigger:** When writing or updating coding standard skills in `.claude/skills/`

**Warning:** Use prohibitive language ("NEVER flag X", "DO NOT suggest Y") rather than permissive language ("X is acceptable") when you want agents to leave code alone. Permissive language invites unnecessary optimization attempts.

**Target doc:** `docs/learned/commands/tripwires.md` (affects skill authoring)

This is tripwire-worthy because the distinction between "acceptable" and "preferable" has real consequences for review bot accuracy. The pattern can manifest across many different coding rules, not just ternary operators.

### 3. Dignified Skill Coordination

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** When editing coding standard skills in `.claude/skills/dignified-*`

**Warning:** Check if updates are needed in BOTH dignified-code-simplifier (guides review/refactoring agents) AND dignified-python-core (guides implementation agents). Coding standards should be consistent across review and authoring contexts.

**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because it's not immediately obvious that standards are duplicated across two skills. The harm is inconsistent agent behavior - different standards applied when reviewing vs writing code.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. "Declare Variables Close to Use" Misapplication

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** The rule "declare variables close to use" was being misapplied to one-line ternary assignments, where the variable IS close to use (same line as assignment). This is a specific instance of over-eager rule application. The ternary guidance update addresses this directly, so a separate tripwire may be redundant. Would promote if the pattern recurs with other rules.

### 2. Workspace Configuration After Package Rename

**Score:** 3/10 (Non-obvious +2, Destructive potential +1)

**Notes:** When renaming packages, workspace glob patterns may still match the directory but the directory lacks required files (`pyproject.toml`). This causes CI failures that look unrelated to the rename. Score is 3 because it's specific to workspace configuration and package rename operations, which are relatively rare. Would promote if the pattern recurs.

### 3. Pre-Existing CI Failure Triage

**Score:** 2/10 (Non-obvious +2)

**Notes:** Agents should check git history to verify whether CI failures predate current work before attempting fixes. The implementation session handled this correctly. Score is 2 because good CI failure triage is general engineering practice rather than erk-specific. Would promote if agents repeatedly attempt out-of-scope CI fixes.

## Implementation Notes

### No New Documentation Files Needed

This is an unusual learn plan in that it generates **zero documentation items**. This is correct because:

1. **Skill files are self-documenting**: The changes to `dignified-code-simplifier/SKILL.md` and `dignified-python/dignified-python-core.md` ARE documentation. They directly inform agents about coding standards.

2. **Code removal needs no docs**: The erkbot agent module was never used - there are no users to migrate, no behaviors to explain, no patterns to document.

3. **Valuable learnings are cross-cutting**: The insights about API contamination, language effectiveness, and skill coordination apply broadly across the erk project. They belong in tripwires (which fire on action patterns) rather than feature documentation (which describes specific functionality).

### Tripwire Implementation Priority

1. **Cross-language API contamination** (universal-tripwires.md) - Highest value, prevents hallucinated suggestions
2. **Skill coordination** (architecture/tripwires.md) - High value, ensures consistent standards
3. **Permissive vs prohibitive language** (commands/tripwires.md) - Medium value, improves skill authoring

### Attribution

| Item | Source | Session |
|------|--------|---------|
| Cross-language API hallucination | Planning session | 076623d0 |
| Skill language effectiveness | Planning session | 076623d0 |
| Skill coordination pattern | Implementation session | eb0df2ff |
| Pre-existing CI handling | Implementation session | eb0df2ff |
| All code inventory items | Diff analysis | PR #8080 |
