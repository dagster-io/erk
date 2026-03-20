# Objective Package — Design Notes

Design decisions and context from the initial design session. This captures the reasoning behind the README — the "why" behind the "what."

## Origin and Motivation

The objective feature existed inside erk as a tightly coupled subsystem. The goal is to extract it as a conceptually independent package that:

- Can be adopted incrementally by users who don't use erk
- Works from any TUI or harness (Claude Code, Codex, etc.)
- Assumes skills and CLI are available
- Lives in the erk uv workspace as `packages/objective/`
- May depend on `erk-shared` for infrastructure (gateways, metadata blocks) — this is acceptable for now

The package is a **thin facade**. The goal is to design what appears to be an independent package. Actual internal dependencies on erk-shared (and even erk) are acceptable during the transition. What matters is the API surface and conceptual boundary.

## Key Design Decisions

### Facade-first, not extraction-first

We are not physically untangling imports today. We're building a new CLI and skill surface from scratch, then wiring it to existing code. The implementation can delegate to erk-shared or even call into erk internals — what matters is that the public API presents a clean, self-contained interface.

### Skills vs CLI commands

The surface is split into two categories:

- **Skills** (LLM-powered, interactive): `create`, `update`, `next`
- **CLI commands** (mechanical, deterministic): `list`, `show`, `check`, `node`, `note`, `close`

`create` is a skill because objective creation is a research process — the agent interviews the user, explores the codebase, and proposes a structured roadmap. It is not a simple CLI command.

`update` is a skill because re-evaluation requires LLM reasoning to compare PR diffs against the roadmap, read notes, and propose changes.

`next` is a skill because it synthesizes context from the objective, the log, and the codebase into a briefing for the next piece of work.

### `objective:next` replaces `erk:objective-plan`

The current `erk:objective-plan` tightly couples "pick a node" with "create an erk plan PR." The new `objective:next` decouples these:

1. Shows your objectives and unblocked nodes
2. Briefs you on context for the selected node
3. Hands off — you decide what to do next

This allows direct implementation without requiring a formal plan. The current system forces you through plan creation → plan save → plan implement. The new system just says "here's what you need to know, go."

### `objective:update` is adversarial

The update skill does not trust the current roadmap. It validates every claim:

- For each remaining node: grep the codebase for the files, functions, and patterns it references
- For each dependency: verify the ordering still holds
- For each design decision: check if the PR contradicted or refined it
- Surface what the PR revealed that the roadmap didn't anticipate

This is a deliberate design choice. The current system (`objective-update-with-landed-pr`) does prose reconciliation as an afterthought. The new system leads with skepticism.

### `objective:update` unifies three existing skills

The current system has three separate skills for objective updates:

1. `objective-update-with-landed-pr` — after a PR merges
2. `objective-update-with-closed-plan` — after a plan is abandoned
3. `objective-reevaluate` — manual audit

These are all variations of "something happened, re-evaluate the objective." The new `objective:update` replaces all three:

- With `--pr`: reads the PR, marks nodes, re-evaluates
- Without `--pr`: standalone codebase audit

The trigger (PR landed, plan closed, manual) doesn't change what the skill does — it always re-evaluates everything.

### Many-to-many: nodes and PRs

The current system has a 1:1 relationship (each node has one `pr` field). The new system supports many-to-many:

- A node can have multiple PRs (work was split)
- A PR can be linked to multiple nodes (one PR addressed several steps)
- A node is "done" when marked done — having PRs linked is evidence, not an automatic trigger

This reflects how work actually happens. A refactor PR might knock out three nodes. A large node might take two PRs.

### The log as append-only journal

The objective issue's comment thread serves as an immutable log. Notes, action summaries, and context from any source accumulate here. The update skill reads the full log when re-evaluating.

Anyone can post to the log: humans, agents, CI, code review processes. Notes are just text — no labels, no machine-readable tags. The update skill reads them and reasons about their content.

### Storage model — three tiers

1. **Structural metadata** (issue body YAML) — source of truth for nodes, statuses, dependencies, PR links. Canonical data, not derived. CLI commands mutate it directly.

2. **Prose** (first comment) — goals, design decisions, implementation context. A mix of primary data (user's original intent, constraints, decisions) and derived state (implementation context, exploration notes). The primary data cannot be reconstructed. The derived parts can be refreshed by `objective:update`.

3. **Comment log** (subsequent comments) — append-only, never edited or deleted. The durable record of what happened and why. Notes, action comments, update reports.

The issue body is formally structured. The comments are the immutable log. You could theoretically reconstruct the derived portions of the prose by examining the log and inspecting the codebase — but the user's original intent is primary data that must be preserved.

### No `--label` on notes

We considered adding `--label` flags to notes (e.g., `--label discovery`, `--label review`). Rejected: notes are just text. The update skill reads them and reasons about what they mean. Adding machine-readable structure is unnecessary complexity.

### Rewind as a composed pattern, not a command

Rewind (resetting nodes after a failed or abandoned implementation) is not a dedicated command. It's composed from existing primitives:

1. `objective node 42 2.1 2.2 --status pending --unlink-pr 412` — reset nodes
2. `objective note 42 "Reverted nodes 2.1-2.3, PRs discarded because..."` — explain why

The note is essential for context hygiene. Without it, the log contains stale entries about the now-discarded work, and the next `objective:update` would treat them as ground truth. The note tells the update skill to discount prior context about those nodes.

This matters most in automated scenarios where an agent implements multiple nodes without human steering. If confidence degrades across a sequence of implementations, you need to rewind and start fresh with a clean context.

### `erk objective` stays unchanged

The existing `erk objective` commands and skills are not modified. The new `objective` package is a parallel, from-scratch prototype. Once it stabilizes, it may replace the erk commands — but for now they coexist.

## Integration Points

### With `erk land`

`/objective:update` runs automatically after landing a PR linked to an objective. This is the primary integration point. Erk's land command invokes the skill.

### What stays in erk (not in the objective package)

- Creating plans from objective nodes (plan concept)
- Land command integration (calls into objective:update)
- TUI objective nodes screen (imports from objective package)
- One-shot dispatch from objective nodes
- Slug generation via LLM

These are erk integrations built on top of the objective API.

## Dependency Direction

```
erk-shared  <--  objective  <--  erk
```

The objective package imports from erk-shared (gateways, metadata infra). Erk imports from objective for integration points. The objective package never imports from erk.

## Package Structure

```
packages/objective/
├── README.md              # User-facing documentation (the product spec)
├── DESIGN.md              # This file (design decisions and context)
├── pyproject.toml          # deps: erk-shared, click, pyyaml, rich
├── src/objective/
│   ├── __init__.py
│   ├── validation.py       # roadmap validation
│   ├── operations/         # one module per CLI command
│   │   ├── create.py
│   │   ├── show.py
│   │   ├── list.py
│   │   ├── check.py
│   │   ├── close.py
│   │   ├── node.py
│   │   └── note.py
│   └── cli/
│       └── cli.py          # Click group
├── skills/
│   ├── objective-create.md
│   ├── objective-update.md
│   └── objective-next.md
└── tests/
```

## Full Surface Summary

| Name                | Type  | Purpose                                               |
| ------------------- | ----- | ----------------------------------------------------- |
| `/objective:create` | skill | Guided creation with codebase research                |
| `/objective:update` | skill | Adversarial re-evaluation after work or new context   |
| `/objective:next`   | skill | "What should I work on?" — briefing and handoff       |
| `objective list`    | CLI   | List objectives with sparkline progress               |
| `objective show`    | CLI   | Display one objective's roadmap                       |
| `objective check`   | CLI   | Validate structure                                    |
| `objective node`    | CLI   | Mechanical node CRUD (status, PR links, descriptions) |
| `objective note`    | CLI   | Append context to the immutable log                   |
| `objective close`   | CLI   | Close a completed objective                           |
