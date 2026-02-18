---
title: Session File Lifecycle and Persistence
read_when:
  - "working with Claude Code session files across workflows"
  - "implementing learn or analysis workflows that consume session data"
  - "debugging missing session files in plan-based workflows"
tripwires:
  - action: "accessing a session by ID without checking existence first"
    warning: "Session files are session-scoped — Claude Code may clean them up at any time. Always use LBYL discovery (ClaudeInstallation.find_session_globally) before reading."
  - action: "failing a workflow because a session file is missing"
    warning: "Missing sessions must never cause hard failure. Degrade through the fallback hierarchy: planning → implementation → gist → local scan → skip."
  - action: "constructing session file paths manually"
    warning: "Use ClaudeInstallation ABC methods, not manual path construction. Storage layout is an implementation detail that may change."
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# Session File Lifecycle and Persistence

This document explains _why_ session file availability is unreliable and the architectural decisions that flow from that constraint. The core problem: erk workflows (learn, analysis) often need session data from _previous_ Claude Code sessions, but Claude Code owns the session storage lifecycle and may clean up files at any time. Erk cannot control this policy.

## The Fundamental Constraint

Session JSONL files are managed by Claude Code, not erk. Their lifetime is tied to the Claude Code session that created them, with no guaranteed persistence beyond that. This means a session ID stored in GitHub issue metadata (plan-header fields, issue comments) may point to a file that no longer exists on disk.

This constraint drives two architectural decisions:

1. **All session access must go through discovery** — never assume an ID maps to a file
2. **All session-consuming workflows must degrade gracefully** — missing data narrows scope but never causes failure

## Three Storage Tiers

Session data lives in three places with different persistence guarantees. Understanding which tier you're working with determines how you handle availability.

| Tier               | Location                                 | Persistence                                  | Purpose                                                                     |
| ------------------ | ---------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------- |
| **Claude-managed** | `~/.claude/projects/<project>/sessions/` | Unpredictable — Claude Code controls cleanup | Primary session storage; most workflows start here                          |
| **Gist-uploaded**  | GitHub secret gist (URL in plan-header)  | Durable until manually deleted               | Cross-session persistence for learn workflows                               |
| **Scratch**        | `.erk/scratch/sessions/<session-id>/`    | 1 hour TTL, auto-cleaned                     | Inter-process file passing within a single session (e.g., preprocessed XML) |

The key insight: scratch storage is _not_ a session archive — it exists for transient artifacts like preprocessed XML files that a hook produces for Claude to read. The 1-hour TTL is deliberately aggressive because scratch files become stale once the producing session ends.

<!-- Source: packages/erk-shared/src/erk_shared/scratch/scratch.py, cleanup_stale_scratch -->

See `cleanup_stale_scratch()` in `packages/erk-shared/src/erk_shared/scratch/scratch.py` for the TTL-based cleanup logic.

## Why Gist-Based Persistence Exists

The gist upload tier was added because learn workflows frequently run in a _different_ Claude Code session from the one that created or implemented the plan. By the time learn runs, the original session file is often gone. Uploading to a gist and recording the URL in the plan-header creates a durable reference that survives session cleanup.

<!-- Source: src/erk/cli/commands/exec/scripts/upload_session.py, upload_session -->

See `upload_session()` in `src/erk/cli/commands/exec/scripts/upload_session.py` for how gist creation and plan-header updates are coordinated.

## Discovery Architecture

Session discovery has two distinct paths because plan-aware and plan-unaware workflows need fundamentally different information.

| Path             | Command                               | Starting point        | What it knows                                                           |
| ---------------- | ------------------------------------- | --------------------- | ----------------------------------------------------------------------- |
| **Plan-unaware** | `erk exec list-sessions`              | Local filesystem scan | Only what's on disk right now — no plan context                         |
| **Plan-aware**   | `erk exec get-learn-sessions <issue>` | GitHub issue metadata | All sessions ever tracked for a plan, plus which are currently readable |

### Why two paths matter

`list-sessions` can never find sessions from other machines or prior Claude Code lifecycles — it only sees the local project directory. `get-learn-sessions` starts from GitHub metadata and checks readability, so it can identify gist-based remote sessions that `list-sessions` would never discover. It also provides the categorization (planning vs. implementation vs. learn) that analysis workflows need.

<!-- Source: packages/erk-shared/src/erk_shared/sessions/discovery.py, find_sessions_for_plan -->

See `find_sessions_for_plan()` in `packages/erk-shared/src/erk_shared/sessions/discovery.py` for how plan-specific discovery extracts session IDs from multiple metadata sources (plan-header fields, impl-started/impl-ended comments, learn-invoked comments).

### The local fallback decision

<!-- Source: src/erk/cli/commands/exec/scripts/get_learn_sessions.py -->

Local fallback scanning (implemented in `src/erk/cli/commands/exec/scripts/get_learn_sessions.py`) only triggers when **no** GitHub-tracked sessions are readable on disk. This is intentional: local scan results have no confirmed relationship to the plan, so mixing them with plan-tracked sessions would dilute signal. They're a last resort, not a supplement.

When the local fallback triggers, it filters sessions by the current git branch to prevent worktree slot reuse contamination. Worktree slots are reused for different plans over time, so older sessions in the same project directory may belong to an entirely different branch. The `gitBranch` field in each session's JSONL log is matched against the current worktree branch to exclude stale sessions.

## Graceful Degradation Hierarchy

When a workflow needs session data, it walks a priority-ordered hierarchy. Each level represents less certainty about plan relevance but still provides value.

| Priority | Source                                               | Why it might be missing                                                |
| -------- | ---------------------------------------------------- | ---------------------------------------------------------------------- |
| 1        | Planning session (from plan-header)                  | Created in a prior Claude Code session, since cleaned up               |
| 2        | Implementation session (from plan-header + comments) | Same lifecycle issue                                                   |
| 3        | Remote gist session                                  | Gist deleted; requires download step                                   |
| 4        | Legacy artifact session (GitHub Actions run)         | Artifacts expire after 90 days                                         |
| 5        | Local fallback scan                                  | No metadata link to plan — recent sessions may still be relevant       |
| 6        | Skip analysis                                        | Always available — produces no session insights but workflow continues |

### Anti-pattern: hard failure on missing session

Never `exit 1` or raise when a session file is unavailable. The entire hierarchy exists because session availability is _inherently unreliable_. Log a warning and degrade to the next level.

### Anti-pattern: direct path construction

Don't build session paths manually (e.g., `~/.claude/projects/.../sessions/{id}.jsonl`). The `ClaudeInstallation` ABC provides `find_session_globally()` for existence checks and `get_session_path()` for path resolution. Direct construction bypasses the abstraction and breaks if Claude Code changes its storage layout.

## Preprocessing as a Cross-Cutting Concern

Session preprocessing (JSONL-to-XML compression) sits at the boundary between session storage and session consumption. It achieves ~75-84% size reduction by stripping metadata, deduplicating command documentation, and truncating tool parameters. The key architectural choice: preprocessing writes to scratch storage, not back to the session tier, because compressed XML is a derived artifact with a short useful life.

For preprocessing details (compression metrics, chunking algorithm, output modes), see [Session Preprocessing](preprocessing.md).

## Related Documentation

- [Session Discovery and Fallback](discovery-fallback.md) — Discovery commands, output schemas, and the fallback hierarchy in detail
- [Session Preprocessing](preprocessing.md) — Compression metrics, chunking algorithm, and output modes
- [Plan Lifecycle](../planning/lifecycle.md) — How plan-header metadata tracks session references
