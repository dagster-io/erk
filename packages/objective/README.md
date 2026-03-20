# Objective

Track multi-step work as structured roadmaps in GitHub issues. As you complete PRs, an intelligent update loop re-evaluates remaining work based on what you learned and what changed.

## Why

Large tasks span multiple PRs. Without structure, you lose track of what's done, what's next, and what changed since you started. Objective gives you:

- A **roadmap** with phases, dependencies, and status tracking stored in a GitHub issue
- A **dependency graph** that knows which steps are unblocked
- An **update loop** that re-evaluates the plan after each PR, catching stale assumptions and surfacing new work
- An **immutable log** where any process can post context that informs future updates

## Concepts

An **objective** is a GitHub issue with structured metadata. It contains:

- **Phases** — ordered groups of work (e.g., "Phase 1: Preparation")
- **Nodes** — individual steps within a phase, each typically one PR
- **Dependencies** — nodes can depend on other nodes
- **Status** — each node tracks: `pending`, `in_progress`, `done`, `blocked`, `skipped`
- **PR links** — many-to-many: a node can have multiple PRs, and a PR can be linked to multiple nodes

The objective issue is the single source of truth. All tools read from and write to it.

### The Log

The objective issue's comment thread is an append-only log. Notes, action summaries, and context from any source accumulate here — humans, agents, CI, code reviews. The update skill reads the full log when re-evaluating.

## Workflow

```
/objective:create          skill: guided creation with codebase research
    |
objective show 42          CLI: see roadmap and what's next
    |
[do the work, open PRs]
    |
objective note 42          CLI: post context, discoveries, review feedback
    |
/objective:update 42       skill: re-evaluate after completing work
    |
[repeat until done]
    |
objective close 42         CLI: close the objective
```

## Skills

Skills are LLM-powered operations that require reasoning and conversation.

### `/objective:create`

Guided objective creation. The agent interviews you about what you want to accomplish, explores the codebase to understand context, and proposes a structured roadmap for your approval.

```
> /objective:create

What do you want to accomplish?

> I need to migrate our auth middleware. The current implementation stores
> session tokens in a way that doesn't meet compliance requirements...

[agent explores codebase, asks clarifying questions]
[agent proposes phased roadmap]
[you iterate until satisfied]
[agent creates GitHub issue]

Objective #42 created: https://github.com/org/repo/issues/42
```

The creation process:

1. **Interview** — asks what you want to accomplish, constraints, decisions already made
2. **Research** — explores the codebase to verify assumptions and gather context
3. **Structure** — proposes phases, nodes, dependencies, and acceptance criteria
4. **Iterate** — you refine until the roadmap reflects reality
5. **Publish** — creates the GitHub issue with structured metadata

### `/objective:update`

The core of the tool. After completing a PR (or at any point), re-evaluates the objective against what actually happened and what changed on the ground.

```
> /objective:update 42 --pr 456

Updating objective #42 after PR #456...

Reading PR #456...
Reading 3 new notes since last update...

  - "Auth service also caches tokens in Redis"
  - "Need backwards compat for 30 days"
  - "Token format v2 spec changed (RFC-1234)"

PR #456 is linked to node 2.1. Based on the diff, it also addressed
work described in nodes 1.1 and 1.2.

Proposed:
  1. Link PR #456 to nodes 1.1, 1.2
  2. Mark nodes 1.1, 1.2, 2.1 as done
  3. Update node 2.2: "Migrate database schema to new token format"
     (token migration already handled in #456)
  4. Add node 2.4: "Backwards-compatible token validation for 30 days"
     (from review feedback in notes)
  5. Add node 2.5: "Handle Redis cache invalidation during migration"
     (from discovery note)

Apply? [y/n]
```

What it does:

1. **Reads the PR** — diff, description, review comments
2. **Reads the log** — notes and context posted since the last update
3. **Marks completed nodes** — links the PR, infers which nodes it addressed
4. **Adversarially re-evaluates the roadmap** — distrusts the current roadmap and validates every claim:
   - For each remaining node: is this still necessary? Is the description still accurate against the actual codebase? Grep for the files, functions, and patterns it references.
   - For each dependency: does this ordering still hold? Did the PR change what's possible?
   - For each design decision in the prose: is this still true? Did the PR contradict or refine it?
   - What did the PR reveal that the roadmap didn't anticipate? New steps, new risks, changed scope?
   - What did the notes and log entries surface that the roadmap doesn't account for?
5. **Proposes changes** — presents findings with evidence from the PR, notes, and codebase
6. **Applies approved changes** — updates the GitHub issue

Without a PR (standalone re-evaluation):

```
> /objective:update 42
```

Audits the objective against the codebase without a specific PR. Useful when time has passed or other work has landed that might affect the objective.

### `/objective:next`

The "what should I work on?" entry point. Shows your objectives, helps you pick a node, briefs you on context, and lets you start working immediately.

```
> /objective:next

  #42  Migrate auth middleware     ✓✓✓▶○  3/5
  #38  Refactor gateway layer      ✓✓○○○○  2/6

Which objective? [42]

  Phase 2: Implementation
    2.1 ✓ Implement new middleware                 #412 #415
    2.2 ○ Write migration script           -> needs 2.1  [unblocked]
    2.3 ○ Remove old middleware             -> needs 2.2

Next unblocked: 2.2 — Write migration script

Here's what you need to know for node 2.2:
  - The migration script needs to handle the v2 token format (RFC-1234)
  - Redis cache invalidation is required (note from 2026-03-15)
  - PR #412 reviewer flagged 30-day backwards compat requirement
  - Key files: src/auth/tokens.py, src/auth/middleware.py

Ready to start?
```

What it does:

1. **Lists your objectives** — shows progress sparklines, highlights which have unblocked work
2. **Shows unblocked nodes** — filters by dependency graph, recommends the next one
3. **Briefs you** — synthesizes objective context, the log (notes, prior updates), and relevant codebase state into a concise briefing for the selected node
4. **Hands off** — you decide what to do next: start coding, create a formal plan, dispatch to another agent. The skill doesn't prescribe a workflow.

If you only have one objective with one unblocked node, it skips straight to the briefing.

## CLI Commands

Mechanical operations that don't require LLM reasoning.

### `objective list`

List all open objectives with sparkline progress.

```
$ objective list

  #42  Migrate auth middleware     ✓✓✓▶○  3/5   next: 2.2
  #38  Refactor gateway layer      ✓✓○○○○  2/6   next: 1.3
  #51  Add caching                 ○○○     0/3   next: 1.1
```

### `objective show <ref>`

Display a single objective's full roadmap.

```
$ objective show 42

  #42: Migrate auth middleware          ✓✓✓▶○ 3/5

  Phase 1: Preparation
    1.1 ✓ Audit existing session storage          #401
    1.2 ✓ Define new token format spec             #401 #403

  Phase 2: Implementation
    2.1 ✓ Implement new middleware                 #412 #415
    2.2 ○ Write migration script           -> needs 2.1
    2.3 ○ Remove old middleware             -> needs 2.2
```

### `objective check <ref>`

Validate an objective's structure. Reports malformed metadata, broken dependencies, or inconsistent state.

```
$ objective check 42
Objective #42: 5 nodes, 2 phases, 0 errors
```

### `objective node <ref> <node-id...>`

Mechanical node operations. Link PRs, change status, update descriptions.

```bash
# Link a PR to a node
objective node 42 2.1 --link-pr 412

# Same PR covers multiple nodes
objective node 42 2.1 2.2 --link-pr 412

# Second PR on same node
objective node 42 2.1 --link-pr 415

# Unlink a PR
objective node 42 2.1 --unlink-pr 412

# Change status
objective node 42 2.1 --status done

# Update description
objective node 42 2.2 --description "Migrate database schema to new token format"
```

### `objective note <ref>`

Post context to the objective's log. Append-only.

```bash
# Inline
objective note 42 "Auth service also caches tokens in Redis. Node 2.2 needs cache invalidation."

# From stdin
echo "CI found 3 additional test files that need migration" | objective note 42

# From a file
objective note 42 --file findings.md

# Context from various sources
objective note 42 "Token format v2 spec changed, see RFC-1234"
objective note 42 "PR #412 reviewer flagged: need backwards compat for 30 days"
```

### `objective close <ref>`

Close a completed objective.

```bash
objective close 42
```

## Patterns

### Rewinding Work

When automated implementation loses confidence — or when a PR is abandoned for any reason — you can reset nodes and disassociate PRs using existing primitives:

```bash
# Reset nodes and disassociate PRs
objective node 42 2.1 2.2 2.3 --status pending --unlink-pr 412 --unlink-pr 413

# Post a rewind note to prevent context pollution
objective note 42 "Reverted nodes 2.1-2.3. PRs #412, #413 discarded.
Implementation diverged from requirements after node 2.1. Design decisions about
token caching from the 2026-03-15 update no longer apply."
```

The note is essential for context hygiene. Without it, the log still contains entries like "marked 2.1 as done" and notes about decisions made during the now-discarded work. The next `/objective:update` would treat that stale context as ground truth.

The update skill reads the full log chronologically. When it sees a note explaining that nodes were reverted, it discounts prior log entries about those nodes and re-evaluates them from scratch.

This matters most in automated scenarios where an agent implements multiple nodes in sequence without human steering. If node 2.3's implementation was built on a bad assumption in node 2.1, you need to rewind all three and start fresh — and the objective's context needs to reflect that cleanly.

## Data Model

### Many-to-Many: Nodes and PRs

Nodes and PRs have a many-to-many relationship:

- A node can have multiple PRs (work was split across PRs)
- A PR can be linked to multiple nodes (one PR addressed several steps)
- A node is "done" when marked done — having PRs linked is evidence, not an automatic trigger

### Node Status

| Status        | Symbol | Meaning               |
| ------------- | ------ | --------------------- |
| `pending`     | `○`    | Not started           |
| `in_progress` | `▶`   | Work underway         |
| `done`        | `✓`    | Completed             |
| `blocked`     | `⊘`    | Waiting on dependency |
| `skipped`     | `-`    | Won't do              |

### Storage

Everything lives in the GitHub issue:

- **Issue body** — structured metadata: roadmap phases, nodes, dependencies, status, PR links
- **First comment** — objective prose: goals, design decisions, implementation context
- **Subsequent comments** — the immutable log: notes, action summaries, update reports

The issue body contains **structured metadata blocks** (YAML) that are the source of truth for the roadmap: nodes, statuses, dependencies, and PR links. This is canonical data, not derived — CLI commands like `objective node` mutate it directly.

The **first comment** contains the objective's prose: goals, design decisions, implementation context. Some of this is primary data — the user's original intent, their stated constraints, decisions they made — which cannot be reconstructed. Other parts (implementation context, exploration notes) are derived from codebase state and can be refreshed by `/objective:update` when they drift.

The **comment log** is append-only and must never be edited or deleted — it's the durable record of what happened and why.

## Integration

### With `erk land`

`/objective:update` runs automatically after landing a PR linked to an objective. No manual invocation needed.

### With any CI/CD

```yaml
- name: Update objective
  run: objective update $OBJECTIVE_NUMBER --pr ${{ github.event.pull_request.number }}
```

### With manual workflows

```bash
# When starting work
objective node 42 2.1 --status in_progress --link-pr 412

# Post context as you go
objective note 42 "Found that X also needs Y"

# When the PR merges
/objective:update 42 --pr 412
```
