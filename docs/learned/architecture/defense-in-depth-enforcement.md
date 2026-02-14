---
title: Defense-in-Depth Enforcement
read_when:
  - designing multi-layer validation or enforcement systems
  - implementing critical rules across multiple components
  - understanding why erk uses redundant enforcement mechanisms
tripwires:
  - action: "relying solely on agent-level enforcement for critical rules"
    warning: "Add skill-level and PR-level enforcement layers. Only workflow/CI enforcement is truly reliable."
    score: 7
---

# Defense-in-Depth Enforcement

Defense-in-depth enforcement implements the same rule at multiple independent layers. When one layer fails, downstream layers catch the violation. This creates resilient systems where critical rules are enforced even when individual enforcement mechanisms break.

## Why Multiple Layers Matter

Single-layer enforcement fails because each layer has distinct failure modes:

- **Agent instructions** are non-deterministic (misinterpreted, ignored, or missed due to context limits)
- **Skill guidance** depends on loading timing (may not load, or load after violation occurs)
- **Manual review** is inconsistent (reviewers miss issues, don't always follow guidelines)

Critical rules—those that create bugs, tech debt, or maintenance burden when violated—require deterministic enforcement. Only automated PR checks running on every submission provide this guarantee.

## The Reliability Hierarchy

Not all layers are equally reliable. From least to most reliable:

| Layer               | Reliability | Why It Fails                                                                  |
| ------------------- | ----------- | ----------------------------------------------------------------------------- |
| Agent instructions  | Lowest      | Non-deterministic, context-dependent, can be overridden by competing guidance |
| Loaded skills       | Low         | Timing-dependent, can be loaded after violations already written              |
| Manual review       | Medium      | Human consistency issues, different reviewers catch different things          |
| Automated PR checks | Highest     | Deterministic, runs on every PR, provides exact source locations              |

**Key insight:** Defense-in-depth means upstream layers reduce burden on downstream layers, but downstream layers must exist for critical rules.

<!-- Source: docs/learned/planning/reliability-patterns.md:38-63 -->

For deeper discussion of deterministic vs non-deterministic operations, see `reliability-patterns.md` in `docs/learned/planning/`.

## When to Use Defense-in-Depth

Apply this pattern when rule violations create tangible problems:

**Use defense-in-depth for:**

- Technical debt (stale code blocks, duplicate imports)
- Bugs (missing required fields, incorrect types)
- Security issues (exposed credentials, unsafe patterns)
- Breaking changes (API contract violations)

**Don't use defense-in-depth for:**

- Style preferences (one enforcement layer sufficient)
- Non-critical guidelines (agent instructions only)
- Patterns with high false positive rates (review fatigue)

The decision test: "If this rule is violated, does it create work for someone later?" If yes, implement multiple layers.

## Measuring Layer Effectiveness

Track where violations are caught to identify weak layers:

| Where Caught       | Interpretation                | Action                             |
| ------------------ | ----------------------------- | ---------------------------------- |
| Layer 1 (agent)    | Ideal—lowest cost             | None needed                        |
| Layer 2 (skill)    | Good—caught pre-PR            | None needed                        |
| Layer 3 (PR check) | Acceptable—safety net working | Consider improving upstream layers |
| Production         | **Failure**—all layers failed | Add or fix enforcement layers      |

If Layer 3 consistently catches violations, it indicates:

1. Upstream layers (1-2) need better detection or clearer guidance
2. The rule might be unintuitive (consider simplifying)
3. Layer 3 is correctly functioning as the fail-safe

Don't remove Layer 3 even if upstream layers improve—it's the only truly reliable enforcement.

## Example: Verbatim Code Block Prevention

Erk prevents verbatim code blocks in `docs/learned/` using three enforcement layers:

<!-- Source: .claude/agents/learn/code-diff-analyzer.md:109-117 -->
<!-- Source: .claude/skills/learned-docs/learned-docs-core.md:49-63 -->
<!-- Source: .github/reviews/audit-pr-docs.md:50-78 -->

**Layer 1 - Agent (code-diff-analyzer):** When analyzing PR diffs for documentation needs, detects code blocks and suggests source pointers. See `code-diff-analyzer.md` in `.claude/agents/learn/`.

**Layer 2 - Skill (learned-docs):** When loaded during doc writing, instructs agents to use source pointers instead of verbatim code. See `learned-docs-core.md` in `.claude/skills/learned-docs/`.

**Layer 3 - Automated PR Review (audit-pr-docs):** Scans every PR touching `docs/learned/`, posts inline comments for violations with exact source file and line numbers. See `audit-pr-docs.md` in `.github/reviews/`.

Each layer has distinct failure modes:

- Agent may not be invoked for the PR
- Skill may load after code already written
- Automated review is deterministic—always runs, always catches violations

This structure allows incremental development: deploy Layer 3 immediately (guaranteed enforcement), then develop Layers 1-2 to reduce false positives and improve user experience.

## Implementation Strategy

When implementing defense-in-depth enforcement:

1. **Design Layer 3 first**—the deterministic automated check. Don't proceed without this.
2. **Deploy Layer 3 immediately**—before building upstream layers. This establishes the enforcement baseline.
3. **Add upstream layers incrementally**—agent guidance, skill rules. These reduce burden on Layer 3 but don't replace it.
4. **Measure effectiveness**—track which layer catches violations. Use data to improve weak layers.
5. **Never remove Layer 3**—even if upstream layers become highly effective. It's the fail-safe.

## Anti-Pattern: Relying on Upstream Layers Alone

**WRONG:**

```yaml
# Only agent instructions
"Remember to use source pointers instead of verbatim code blocks"
```

**Why it fails:** Agent instructions are non-deterministic. Context limits, competing guidance, or misinterpretation cause violations to slip through.

**CORRECT:**

Add automated PR review that posts inline comments for every violation. Agent instructions become defense-in-depth, not primary enforcement.

## Related Patterns

<!-- Source: docs/learned/ci/workflow-gating-patterns.md:120-174 -->

**Workflow gating:** See `workflow-gating-patterns.md` in `docs/learned/ci/` for multi-layer workflow control using trigger filtering, job conditions, and output-based skipping. Same principle: multiple independent layers providing flexible, safe control.

<!-- Source: docs/learned/planning/reliability-patterns.md:15-63 -->

**Reliability patterns:** See `reliability-patterns.md` in `docs/learned/planning/` for deterministic vs non-deterministic operation classification and the commit-before-reset pattern.

<!-- Source: docs/learned/documentation/stale-code-blocks-are-silent-bugs.md:14-23 -->

**Why verbatim code prevention matters:** See `stale-code-blocks-are-silent-bugs.md` in `docs/learned/documentation/` for the case against embedded code (silent drift, false confidence, no detection).
