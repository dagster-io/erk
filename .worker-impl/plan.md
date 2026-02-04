# Documentation Plan: PR Address: Wrap constants behind @cache + update dignified-python

## Context

This implementation refactored skill registries in erk to follow dignified-python standards. The PR (#6684) wrapped two module-level frozenset collections (`CODEX_PORTABLE_SKILLS` and `CLAUDE_ONLY_SKILLS`) behind `@cache` functions to avoid mutable state at import time. This is a straightforward application of an existing pattern documented in the dignified-python skill.

The primary documentation value from this session comes not from the code changes themselves (which are already documented in the skill), but from the learn pipeline execution patterns observed during the session. The session revealed graceful fallback behaviors, session discovery complexity, and error recovery patterns that future agents would benefit from understanding.

Documentation matters here because agents running `/erk:learn` will encounter the same edge cases: empty gists triggering silent fallbacks, planning sessions being unavailable locally, and token budget constraints during preprocessing. Capturing these operational patterns prevents confusion and enables agents to distinguish expected behavior from actual errors.

## Raw Materials

https://gist.github.com/schrockn/37185b5d4ca332052961731d153c53f9

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 4     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Codex Skills Registries Reference

**Location:** `docs/learned/reference/codex-skills-registries.md`
**Action:** CREATE
**Source:** [PR #6684]

**Draft Content:**

```markdown
---
title: Codex Skills Registries
read_when:
  - "adding a new skill to the registry"
  - "understanding which skills work with Codex vs Claude-only"
  - "working with codex_portable.py"
---

# Codex Skills Registries

The erk codebase maintains two skill registries that distinguish between skills portable to Codex (compatible with multiple AI providers) and skills specific to Claude Code.

## Registry Functions

<!-- Source: src/erk/core/capabilities/codex_portable.py, codex_portable_skills -->
See `codex_portable_skills()` in `src/erk/core/capabilities/codex_portable.py` for the registry of skills that work across AI providers.

<!-- Source: src/erk/core/capabilities/codex_portable.py, claude_only_skills -->
See `claude_only_skills()` in `src/erk/core/capabilities/codex_portable.py` for skills that require Claude-specific features.

## When to Use Each Registry

**Portable skills** (`codex_portable_skills()`):
- Work with any AI provider (Claude, OpenAI, etc.)
- No Claude-specific tool use or features
- Can be bundled for Codex deployments

**Claude-only skills** (`claude_only_skills()`):
- Require Claude Code features (hooks, special tools)
- Not portable to other AI providers

## Adding a New Skill

When adding a skill to the codebase, determine which registry it belongs in:

1. Does the skill use Claude-specific features (hooks, tool restrictions)? → `claude_only_skills()`
2. Is the skill general-purpose documentation or guidance? → `codex_portable_skills()`

## API Pattern

Both registries are wrapped behind `@cache` functions following dignified-python module design standards. Call them as functions:

```python
from erk.core.capabilities.codex_portable import codex_portable_skills, claude_only_skills

# Correct - function calls
portable = codex_portable_skills()
claude_specific = claude_only_skills()
```

This pattern avoids import-time side effects from mutable collections.
```

---

#### 2. Learn Pipeline Resilience Patterns

**Location:** `docs/learned/planning/learn-pipeline-resilience.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Learn Pipeline Resilience Patterns
read_when:
  - "debugging why learn command fell back to local sessions"
  - "understanding gist download failures in learn workflow"
  - "session discovery returning unexpected results"
tripwires:
  - action: "running /erk:learn with gist_url that returns empty"
    warning: "Empty gist indicates preprocessing hasn't completed. This triggers silent fallback to local session discovery. Verify gist upload succeeded or provide no gist_url to skip remote sources."
  - action: "relying on planning_session_id being available locally"
    warning: "Planning sessions may be from earlier branch/run and unavailable locally. Use erk exec get-learn-sessions to verify availability; missing sessions don't block pipeline."
---

# Learn Pipeline Resilience Patterns

The learn pipeline is designed to degrade gracefully when expected data sources are unavailable. Understanding these fallback behaviors helps distinguish expected behavior from actual errors.

## Gist Fallback Pattern

When `/erk:learn` receives a `gist_url` parameter but the gist is empty:

1. The system attempts to download preprocessed materials from the gist
2. Empty response triggers fallback to local session discovery
3. Local sessions are discovered via `erk exec get-learn-sessions`
4. Preprocessing runs locally on discovered JSONL files

**Why this happens:** The `gist_url` is stored in plan metadata before preprocessing completes. On first learn run, the gist may not yet be populated.

**Expected behavior:** This fallback is intentional and does not indicate an error. The learn pipeline continues with locally available data.

## Session Discovery Differences

Sessions come from multiple sources with different availability:

| Source | Availability | Notes |
|--------|-------------|-------|
| Local implementation sessions | Current branch's ~/.claude/ | Always available if run locally |
| Remote implementation sessions | Gist or CI artifacts | Available after upload |
| Planning sessions | May be from earlier branch | Often unavailable locally |

The `planning_session_id` in plan metadata points to the session that created the plan. This session may be:
- From an earlier branch (already merged/deleted)
- From a different worktree
- Only available in remote storage

**Expected behavior:** Missing planning sessions do not block the learn pipeline. Proceed with available sessions.

## Error vs Expected Behavior

| Symptom | Type | Response |
|---------|------|----------|
| Gist download returns empty | Expected | Fallback to local |
| Planning session not in local paths | Expected | Skip, continue with available |
| Preprocessing fails on one session | Expected | Skip that session, continue with others |
| All sessions unavailable | Error | No data to analyze; investigate |

## Related Documentation

- [Learn Workflow](learn-workflow.md) - Full learn workflow architecture
- [Session Preprocessing](session-preprocessing.md) - Token budgets and chunking
```

---

### MEDIUM Priority

#### 1. Session Preprocessing Token Budgeting (UPDATE)

**Location:** `docs/learned/planning/session-preprocessing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content (additions to existing doc):**

Add after the "Size Validation" section:

```markdown
## Token Budget Details

The preprocessing command enforces a 20k token limit by default:

```bash
erk exec preprocess-session --session-file <path> --output <path> --max-tokens 20000
```

**Budget behavior:**
- Sessions within budget: Single XML output file
- Sessions exceeding budget: Automatic chunking to multiple files
- Each chunk is independently valid XML
- Downstream agents receive list of chunk paths

**Monitoring guidance:**
- Target: XML output should stay under 22k tokens (20k content + 2k structure)
- If chunking occurs frequently, consider increasing `--max-tokens` or reducing input session size
- Token overruns are handled gracefully via chunking, not as errors

## Preprocessing Failure Recovery

Preprocessing can fail for certain sessions (corrupted, truncated, malformed JSONL). This is expected behavior:

- Failed sessions are skipped
- Remaining sessions continue processing
- Learn pipeline proceeds with available data
- No retry or manual intervention required

This resilience ensures a single bad session doesn't block the entire learn workflow.
```

---

#### 2. PR Inventory Building in Learn Workflow (UPDATE)

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content (addition to existing doc):**

Add a new section after "The Learn Flow":

```markdown
## PR Inventory Building

Before session analysis begins, the learn pipeline builds a file/function inventory from the PR:

1. **Fetch PR metadata**: Files changed, additions/deletions, diff statistics
2. **Create inventory**: New functions, modified files, scope summary
3. **Pass to analysis agents**: Agents receive scope context before analyzing sessions

**Why inventory first:**
- Sessions may reference changes the agent doesn't know about
- Inventory provides "what changed" context for "why it changed" analysis
- Enables CodeDiffAnalyzer to correlate session patterns with actual changes

**Implementation note:** The CodeDiffAnalyzer runs in parallel with SessionAnalyzer, both in Tier 1. The inventory is built before either agent launches.
```

---

### LOW Priority

#### 1. Session Discovery Documentation (UPDATE)

**Location:** `docs/learned/planning/session-preprocessing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content (addition):**

Add to the "Session Source Types" section:

```markdown
### Source Discovery Behavior

The learn command discovers sessions through multiple code paths:

1. **Gist path**: Download from provided gist_url
2. **Local path**: Scan ~/.claude/projects/ for JSONL files
3. **Remote path**: Fetch from CI artifacts or stored locations

These paths may return different session counts. A planning session from one path may be unavailable in another. This is expected and handled gracefully.

**Authoritative source:** Use `erk exec get-learn-sessions` to get the canonical list of available sessions for a given plan. This command centralizes session source logic and returns consistent results.
```

---

## Contradiction Resolutions

No contradictions found. All code changes align with existing dignified-python documentation standards. The module-design.md file was already updated in the PR to guide the @cache pattern for collections.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Empty Gist on First Learn Run

**What happened:** Gist download returned empty content, triggering fallback to local discovery.
**Root cause:** The `gist_url` was stored in plan metadata before preprocessing completed. On first learn run, the gist hadn't been populated yet.
**Prevention:** Document that gist_url in plan metadata is only meaningful after preprocessing upload completes. On learn runs, expect empty gist on first call and rely on local fallback.
**Recommendation:** ADD_TO_DOC (already captured in learn-pipeline-resilience.md draft)

### 2. Planning Session Unavailable Locally

**What happened:** The `planning_session_id` pointed to a session not present in local `session_paths`.
**Root cause:** Planning session was from an earlier branch/run and not stored locally.
**Prevention:** Accept that planning sessions may be unavailable locally. The learn pipeline should proceed with available sessions rather than treating this as an error.
**Recommendation:** ADD_TO_DOC (already captured in learn-pipeline-resilience.md draft)

### 3. Token Budget Overruns

**What happened:** Some sessions exceeded the 20k token budget, triggering automatic chunking.
**Root cause:** Large session files with many tool calls exceed single-chunk budget.
**Prevention:** Document the chunking behavior as expected, not an error. Downstream agents should handle multiple chunk files.
**Recommendation:** ADD_TO_DOC (already captured in session-preprocessing.md update)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Empty Gist on First Learn Run

**Score:** 4/10 (criteria: Cross-cutting +2, Silent failure +1, Non-obvious +1)
**Trigger:** Before running `/erk:learn` with gist_url parameter
**Warning:** "Empty gist indicates preprocessing hasn't completed. This triggers silent fallback to local session discovery. Verify gist upload succeeded or provide no gist_url to skip remote sources."
**Target doc:** `docs/learned/planning/learn-pipeline-resilience.md`

This is tripwire-worthy because agents may assume the gist_url parameter means data will be downloaded, when in fact empty gists silently fall back to local discovery. Without understanding this, agents may be confused about where session data came from.

### 2. Inconsistent Session Discovery

**Score:** 4/10 (criteria: Cross-cutting +2, Non-obvious +1, Repeated pattern +1)
**Trigger:** Before relying on session availability in learn pipeline
**Warning:** "Session discovery differs by source: local planning sessions may be unavailable (from earlier branch/run), implementation sessions discoverable locally. Use erk exec get-learn-sessions to verify availability; missing sessions don't block pipeline."
**Target doc:** `docs/learned/planning/learn-pipeline-resilience.md`

This is tripwire-worthy because agents frequently encounter "missing" sessions and may treat this as an error requiring investigation. Understanding that planning sessions are often unavailable locally prevents wasted debugging effort.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Token Budget Overflow in Preprocessing

**Score:** 2/10 (criteria: External tool quirk +1, Repeated pattern +1)
**Notes:** The 20k token limit with automatic chunking is working correctly. Not destructive since chunking handles overflow gracefully. Only becomes important if agents exceed budget expectations and don't understand the chunking output format. Recommend monitoring alert rather than hard tripwire.

### 2. Planning Session Unavailable Locally

**Score:** 3/10 (criteria: Non-obvious +1, Cross-cutting +1, Pattern observed +1)
**Notes:** Could be tripwire if agents frequently get confused by missing planning sessions. Currently handled gracefully in the pipeline. Escalate to full tripwire if pattern repeats and causes agent confusion in future learn runs. Already partially covered by the "Inconsistent Session Discovery" tripwire above.