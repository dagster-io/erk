# Documentation Plan: Add `.worker-impl/` cleanup to `pr-address` workflow

## Context

This learn session analyzed PR #7807, which added cleanup of plan staging directories (`.worker-impl/` and `.erk/impl-context/`) to the `pr-address` workflow. The implementation itself was straightforward and well-documented within the PR delivery -- the documentation update was included in the same PR, demonstrating exemplary documentation discipline.

However, the learn pipeline's attempt to analyze this PR revealed important gaps in the **learn workflow itself**. The actual planning and implementation sessions were remote (GitHub Actions), lacked downloadable gist URLs, and the `.erk/impl-context/` directory contained only PR comment JSONs, not session XMLs. This caused the learn session to analyze itself (a meta-session paradox), exposing fragility in remote session discovery.

Documentation matters here not for PR #7807's content (already complete), but for hardening the learn pipeline against similar remote session discovery failures. Future agents launching learn workflows for remote implementations will benefit from explicit guidance on handling unavailable session logs.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 2     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### MEDIUM Priority

#### 1. Remote Session Discovery Fallbacks

**Location:** `docs/learned/planning/remote-session-discovery.md`
**Action:** CREATE
**Source:** [Impl] (meta-session analysis)

**Draft Content:**

```markdown
# Remote Session Discovery in Learn Workflows

<!-- Read-when: launching learn pipeline for remote implementations, get-learn-sessions returns null gist_urls, session logs unavailable -->

## When This Applies

When learning from plans implemented remotely (GitHub Actions), session logs may be unavailable if:

1. The implementation predates gist-based session storage
2. The async learn workflow staged PR comments but not session XMLs
3. Network/permission issues prevented gist creation

## Detection

The `get-learn-sessions` exec script returns session metadata including `gist_url`. When this field is null for remote sessions, the logs cannot be downloaded.

## Fallback Strategy

When session logs are unavailable, proceed with reduced context:

1. **Plan body**: Extract implementation details from the issue body
2. **PR diff**: Analyze code changes directly
3. **PR comments**: Review discussion for insights and corrections
4. **Commit messages**: Understand implementation progression

Document findings with caveat: "Analysis based on plan/PR materials only; session logs unavailable."

## Prevention

For new remote implementations, verify gist URLs are created by checking the plan metadata after implementation completes.

## Related

- See `worktree-cleanup.md` for cleanup patterns
- See `reliability-patterns.md` for multi-layer resilience
```

---

### LOW Priority

#### 2. Validate impl-context Contents

**Location:** `docs/learned/planning/reliability-patterns.md`
**Action:** UPDATE
**Source:** [Impl] (meta-session analysis)

**Draft Content:**

Add a subsection under the existing reliability patterns:

```markdown
## Validating Preprocessed Materials

When the learn pipeline detects `.erk/impl-context/`, it assumes session preprocessing completed. However, async workflows may stage partial materials:

- **PR comment JSONs**: Always present after `pr-address` runs
- **Session XMLs**: Only present if session preprocessing step completed

Before skipping full session discovery, validate that expected files exist:

```bash
# Check for session XMLs, not just directory existence
ls .erk/impl-context/*.xml 2>/dev/null || echo "No session XMLs - run full discovery"
```

If only PR comments exist, execute full session discovery/preprocessing.
```

---

## Contradiction Resolutions

**No contradictions found.** All existing documentation is consistent with PR #7807's implementation:

- `docs/learned/planning/worktree-cleanup.md` correctly updated to include `pr-address.yml`
- `docs/learned/planning/reliability-patterns.md` Layer 3 pattern applies without modification
- `docs/learned/ci/plan-implement-workflow-patterns.md` conceptually compatible

## Stale Documentation Cleanup

**No stale documentation detected.** All file references in existing docs were verified valid.

## Prevention Insights

Errors and failed approaches discovered during the learn pipeline execution:

### 1. Meta-Session Paradox

**What happened:** The learn session attempted to preprocess session `5dcb88be`, which was the current learn session itself, not the implementation session for PR #7807.

**Root cause:** `get-learn-sessions` returned the current session ID in `local_session_ids` because no tracked planning/implementation sessions existed locally. The exec script didn't filter out the requesting session.

**Prevention:** Filter current session ID from `get-learn-sessions` results, or explicitly label it as "current session (not a plan/impl session)."

**Recommendation:** TRIPWIRE

### 2. Remote Sessions Without Gist URLs

**What happened:** The implementation sessions for PR #7807 ran in GitHub Actions but had no downloadable gist URLs, leaving the learn pipeline without session logs.

**Root cause:** Legacy GitHub Actions runs stored sessions as artifacts, not gists. Gist storage was added later, creating a discovery gap for older remote sessions.

**Prevention:** Document the transition point when gist storage started. Provide fallback workflow using plan body + PR diff + PR comments.

**Recommendation:** TRIPWIRE

### 3. Empty impl-context Session XMLs

**What happened:** The `.erk/impl-context/` directory contained only PR comment JSONs, not session XMLs. The learn pipeline assumed preprocessing was complete and skipped full session discovery.

**Root cause:** The async learn workflow stages PR comments separately from session preprocessing. When only the comment staging step completed, impl-context exists but lacks session data.

**Prevention:** Validate impl-context contents (check for XMLs) before skipping session discovery.

**Recommendation:** ADD_TO_DOC (reliability-patterns.md)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Remote Session Download Gaps

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, Internal script -1)

**Trigger:** Before launching learn pipeline for remote implementations

**Warning:** "Check if session_sources contains remote sessions with null gist_url. If unavailable, warn user and fall back to plan/PR analysis only. See remote-session-discovery.md for fallback strategies."

**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the failure is silent -- the learn pipeline continues with degraded context rather than failing loudly. Agents may produce incomplete learn materials without realizing session logs were never downloaded. The pattern affects ALL learn pipeline executions for remote implementations where gist URLs are unavailable.

### 2. Learn Session Analyzing Itself

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)

**Trigger:** When get-learn-sessions returns current session ID in local_session_ids

**Warning:** "This indicates the learn session itself is being detected, not actual implementation sessions. Filter out requesting session ID from results or label as 'current session (not a plan/impl session).'"

**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because detecting your own session ID requires understanding that the learn session exists in the same session directory structure as implementation sessions. Without this awareness, agents waste time preprocessing their own session or generate confusing "session analyzing itself" artifacts.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Legacy Remote Sessions Without Gists

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)

**Notes:** Borderline case -- currently more of a "historical context" issue than an active pattern. Could become a full tripwire if the pattern repeats or if more legacy remote sessions require learn analysis. For now, documenting in `remote-session-discovery.md` is sufficient.

### 2. Empty impl-context Session XMLs

**Score:** 2/10 (criteria: Non-obvious +2)

**Notes:** Rare edge case in async workflow timing. More likely a workflow bug to fix (ensure session preprocessing completes before learn trigger) than a tripwire to document. If the pattern repeats after workflow fixes, promote to tripwire.

## Analysis Notes

### PR #7807 Documentation Quality

PR #7807 itself exemplified documentation discipline:

- Workflow change included documentation update in same PR
- Used source pointers instead of embedding code blocks
- Cross-referenced existing patterns (multi-layer cleanup)
- Updated exactly the right doc (worktree-cleanup.md)
- No review comments requesting clarification
- Audit-pr-docs check passed with 0 violations

**No additional documentation needed for PR #7807's content.** The documentation items in this plan address gaps in the learn pipeline discovered during analysis, not gaps in the delivered work.

### Source Attribution

- **session-analyzer**: Meta-session analysis revealing learn pipeline gaps
- **code-diff-analyzer**: Confirmed PR #7807 documentation complete
- **existing-docs-checker**: Confirmed no duplicates or contradictions
- **pr-comments-analyzer**: Confirmed no review feedback requiring documentation
