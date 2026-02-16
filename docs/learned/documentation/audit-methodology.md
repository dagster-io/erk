---
title: Documentation Audit Methodology
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
read_when:
  - auditing documentation for quality or staleness
  - classifying doc content as duplicative vs high-value
  - understanding why stale documentation harms agents
tripwires:
  - action: "documenting type definitions without verifying they exist"
    warning: "Type references in docs must match actual codebase types — phantom types are the most common audit finding. Verify with grep before committing."
  - action: "bulk deleting documentation files"
    warning: "After bulk deletions, run 'erk docs sync' to fix broken cross-references."
  - action: "classifying constants or defaults in prose as duplicative"
    warning: "Constants and defaults in prose are HIGH VALUE, not DUPLICATIVE. They provide scannability that code alone cannot — an agent shouldn't need to grep to learn a default value."
---

# Documentation Audit Methodology

Erk's documentation audit system prevents three forms of harm: docs that have drifted from reality, docs that contradict code, and docs that describe things that no longer exist. This document captures the cross-cutting reasoning behind the audit approach — for the executable audit process, see `/local:audit-doc` and `/local:audit-scan`.

## Why Audit Documentation?

Stale documentation is worse than no documentation. An agent reading absent docs will investigate the code and find the truth. An agent reading stale docs will confidently act on lies. The audit system exists because documentation in `docs/learned/` is a "token cache" — preserved reasoning that agents trust without re-verifying.

Three layers work together to maintain doc quality:

| Layer                           | When it runs                                  | What it catches                                    |
| ------------------------------- | --------------------------------------------- | -------------------------------------------------- |
| `/local:audit-doc`              | On-demand, deep analysis of one doc           | All harm categories, phantom types, broken paths   |
| `/local:audit-scan`             | On-demand, heuristic triage of all docs       | Prioritizes which docs need deep audit             |
| `.erk/reviews/audit-pr-docs.md` | Automatically on PRs touching `docs/learned/` | Verbatim code copies, inaccurate claims at PR time |

The first two clean up the past; the third prevents new problems.

## How Documentation Causes Harm

### Drifted Documentation

Documentation that was accurate when written but the code changed underneath it. This is the most common and most insidious category because the doc _looks_ correct — it was correct once.

**Why it's harmful**: Agents follow outdated instructions with full confidence. They waste turns trying patterns that no longer work or looking in files that have moved.

**Common drift vectors**:

- File paths after refactoring (a doc says `src/erk/config.py` but the file is now `src/erk/config/core.py`)
- Line number references after code changes
- API descriptions after gateway refactoring

**Response**: Update with source pointers to current implementation, or remove entirely if the section adds no insight beyond what code shows.

### Contradictory Documentation

Documentation that directly conflicts with actual implementation — describing features that don't exist, showing signatures that don't match, or claiming behavior opposite to what code does.

**Why it's harmful**: When docs and code disagree, agents don't know what to trust. This is strictly worse than absence — it creates active confusion.

**Most dangerous subtype — phantom types**: Docs that reference classes, dataclasses, or enums that were never implemented (or were removed). An early audit round found 11 phantom type definitions across 10 documents. Agents tried to import these types and failed silently.

**Response**: Remove immediately. Don't attempt to reconcile — if the doc is wrong, delete or rewrite.

### Outdated Documentation

Documentation about features, workflows, or integrations that no longer exist in the codebase.

**Why it's harmful**: Creates noise when agents search for information. They find docs about removed features and waste turns trying to use them.

**Response**: Delete entirely. Documentation fossils have negative value.

## Why Verification Order Matters

Auditing checks claims from conceptual to mechanical because higher-level inaccuracies invalidate everything beneath them. If a doc's description of how a system works is wrong, there's no point verifying its import paths — the whole section needs rewriting. Phantom types (the most common single finding) sit second because they cause silent failures: agents try to import non-existent classes and get cryptic errors rather than a clear "this doesn't exist."

<!-- Source: .claude/commands/local/audit-doc.md, Phase 4: Verify System Descriptions -->

The full verification procedure and priority ordering is defined in `/local:audit-doc` Phase 4 (Verify System Descriptions).

## The Classification Decision

When auditing, every section gets classified. The key judgment call is between DUPLICATIVE and HIGH VALUE:

| Classification  | Action                      | Signal                                                                          |
| --------------- | --------------------------- | ------------------------------------------------------------------------------- |
| **HIGH VALUE**  | Keep                        | Captures _why_, connects multiple files, decision tables, anti-patterns         |
| **CONTEXTUAL**  | Keep                        | Connects multiple code locations into a narrative code alone can't provide      |
| **DUPLICATIVE** | Replace with source pointer | Restates what code already communicates (signatures, imports, field lists)      |
| **INACCURATE**  | Fix or remove               | States something that doesn't match current code                                |
| **DRIFT RISK**  | Flag                        | Correct today but will silently go stale (specific values, paths, line numbers) |

### The Constants Exception

Constants and default values mentioned in prose are **HIGH VALUE, not DUPLICATIVE** — this is the most common misclassification. When a doc says "the default machine type is `basicLinux32gb`", that provides instant scannability. An agent shouldn't need to grep the codebase to learn a default.

**The distinction**:

- **DUPLICATIVE** = re-expressing what the code already says clearly (field names, parameter types, class hierarchies)
- **HIGH VALUE** = surfacing defaults, magic values, and constants that require code navigation to find

## Anti-Patterns

**Auditing without reading source**: Checking docs against other docs just propagates errors. Every claim must be verified against actual code.

**Over-deleting**: Simplification that removes "why" explanations because they're "not code." Conceptual documentation is the whole point of learned docs — only remove content that duplicates what code already communicates.

**Deleting without fixing cross-references**: Removing content and leaving broken links to it. Always run `erk docs sync` after bulk deletions to regenerate indexes and fix links.

**Pointing to volatile code**: Source pointers should target stable interfaces (ABCs, schemas, config models), not implementation details that change frequently.

## Related Documentation

- [simplification-patterns.md](simplification-patterns.md) — Three proven patterns for reducing doc duplication
- [source-pointers.md](source-pointers.md) — Format for replacing code blocks with references
- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — The deeper case against embedded code
- [Learned Docs Review](../review/learned-docs-review.md) — Automated PR-time quality checking
