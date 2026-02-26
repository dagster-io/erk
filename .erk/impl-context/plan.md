# Documentation Plan: Delete the -t/--tmux feature from `erk codespace connect`

## Context

This PR (#8259) represents a clean, well-executed feature removal that deleted the `-t/--tmux` and `--session` options from the `erk codespace connect` command. The implementation removed the `_tty_session_name()` helper function, simplified the `connect_codespace()` function, and deleted 8 associated test functions. The work was scoped carefully to preserve tmux functionality used by other commands (specifically `build_codespace_tmux_command()` in codespace_run.py used by the `run objective plan` command).

The implementation sessions demonstrate reference-quality execution: 100% first-attempt edit success rate, proper use of parallel devrun verification, and correct adherence to scope boundaries specified in the plan. This is a textbook application of the existing feature removal checklist rather than a source of novel patterns.

No new documentation is recommended because all patterns observed are already documented. The `docs/learned/refactoring/feature-removal-checklist.md` provides comprehensive guidance for exactly this type of work, and both sessions followed documented workflows correctly. The success of this implementation validates existing documentation coverage.

## Raw Materials

See PR #8259 for the complete diff and implementation context.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 0     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 0     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

No items.

### MEDIUM Priority

No items.

### LOW Priority

No items.

## Contradiction Resolutions

None identified. The existing documentation checker found no contradictions, and all referenced file paths are valid.

## Stale Documentation Cleanup

None identified. All existing docs that reference codespace-related files point to valid, existing artifacts.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Session ID Substitution in Subprocess Context

**What happened:** The `impl-signal started` command failed with "session-id-required" because `${CLAUDE_SESSION_ID}` shell variable substitution failed in subprocess context.

**Root cause:** Shell variable substitution for Claude session ID is not available when commands are executed in subprocess contexts.

**Prevention:** Non-critical signal commands already use `|| true` fallback pattern for graceful degradation.

**Recommendation:** CONTEXT_ONLY - This pattern is already documented in planning/impl-lifecycle.md and the commands already have appropriate fallbacks.

**Tripwire Assessment:** Score 1/10 (External tool quirk +1). Does not meet threshold for tripwire status.

## Tripwire Candidates

None identified. No items met the tripwire-worthiness threshold (score >= 4).

## Potential Tripwires

None identified. No items scored 2-3 on the tripwire rubric.

---

## Analysis Summary

### Why Zero Documentation Items?

This PR demonstrates successful execution of existing patterns, not discovery of new ones:

1. **Feature Removal Checklist Applied**: The existing `docs/learned/refactoring/feature-removal-checklist.md` provides comprehensive 7-category guidance for exactly this type of work. The implementation followed it correctly.

2. **Existing Patterns Followed**: All patterns observed in the sessions are already documented:
   - Parallel devrun execution: Documented in devrun agent docs and ci-iteration skill
   - Non-blocking impl-signal: Documented in planning/impl-lifecycle.md
   - Sequential import cleanup: Standard refactoring practice, single-location insight

3. **Cornerstone Test Results**: Each candidate pattern was evaluated:
   - Sequential import cleanup: Single-location insight (belongs in code comments if anywhere)
   - Parallel devrun pattern: Already documented, this usage is just an instance
   - Scope boundary discipline: PR-specific context, not generalizable

### Existing Documentation Coverage

| Doc | Coverage | Assessment |
|-----|----------|------------|
| `docs/learned/refactoring/feature-removal-checklist.md` | Complete feature removal process | **PRIMARY REFERENCE** |
| `docs/learned/cli/incomplete-command-removal.md` | Command/option removal patterns | Partially applicable |
| `docs/learned/cli/codespace-patterns.md` | Codespace command usage | References connect command |

### Session Quality Assessment

Both sessions demonstrate excellent execution quality:

- **Session bb2d2cf3** (Implementation): 6/6 edits succeeded first try, 4 parallel devrun tasks, full workflow completion
- **Session 9e457f38** (CI/Submit): Only 1 iteration needed, single formatting fix

### Skipped Items

| Item | Reason | Existing Doc |
|------|--------|--------------|
| CLI option removal (--tmux, --session) | Already documented | feature-removal-checklist.md |
| Feature removal process | Already documented | feature-removal-checklist.md |
| Breaking change handling | Already documented | feature-removal-checklist.md |
| Parallel devrun pattern | Already documented | devrun agent, ci-iteration skill |
| Non-blocking impl-signal | Already documented | planning/impl-lifecycle.md |
| Sequential import cleanup | Single-location insight | N/A |
| Deleted test functions | Standard cleanup | N/A |
| Scope boundary preservation | PR-specific detail | N/A |

### Reference Implementation Value

This PR is valuable as a **reference implementation** of the feature-removal-checklist.md, not as a source of new knowledge. The clean execution (no failed approaches, 100% edit success rate) validates that existing documentation provides sufficient guidance for feature removal tasks.

## Conclusion

**ZERO documentation items recommended for creation or update.**

This PR represents successful execution of existing patterns. The feature removal checklist proved comprehensive and sufficient. No documentation gaps were identified.
