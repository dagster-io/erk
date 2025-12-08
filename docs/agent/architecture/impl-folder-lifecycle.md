---
title: Implementation Folder Lifecycle
read_when:
  - "working with .impl/ or .worker-impl/ folders"
  - "understanding implementation folder structure"
  - "debugging remote implementation workflows"
  - "understanding what gets committed vs gitignored"
---

# Implementation Folder Lifecycle

The erk system uses two implementation folder patterns: `.worker-impl/` (committed, visible) and `.impl/` (local, never committed). Understanding their lifecycle is critical for debugging remote implementation workflows.

## .worker-impl/ (Committed, Visible)

**Created by:** `create-worker-impl-from-issue` command

**Purpose:** Make plan visible in PR immediately, before implementation starts

**Contains:**

- `plan.md` - Implementation plan
- `issue.json` - Issue reference (number, URL)
- `progress.md` - Progress tracking (updated by `mark-step` command)
- `README.md` - Human-readable explanation

**Lifecycle:**

1. Created before remote implementation starts
2. Committed and pushed to branch
3. Visible in PR diff immediately
4. Deleted after implementation completes successfully
5. Cleanup commit pushed after CI passes

**Committed:** YES - intentionally visible in PR

**Git status:** Tracked file, not in `.gitignore`

## .impl/ (Local, Never Committed)

**Created by:**

- Copy of `.worker-impl/` (remote implementation)
- `erk implement` command (local implementation)
- `erk wt create --from-issue` (local worktree from issue)

**Purpose:** Working directory for implementation, keeps implementation state local

**Contains:**

- `plan.md` - Implementation plan (copied from `.worker-impl/`)
- `issue.json` - Issue reference (copied from `.worker-impl/`)
- `progress.md` - Progress tracking
- `README.md` - Human-readable explanation
- `run-info.json` - Runtime information (session ID, timestamps)

**Lifecycle:**

1. Created at implementation start
2. Exists during implementation only
3. Read by commands for context (issue reference, progress, etc.)
4. Left in place after implementation for user review
5. User manually deletes when done reviewing

**Committed:** NEVER - in `.gitignore`

**Git status:** Untracked, ignored

## Copy Step (Remote Only)

In remote implementation workflows (GitHub Actions), the workflow copies `.worker-impl/` to `.impl/` before implementation:

```bash
cp -r .worker-impl .impl
```

This ensures the implementation environment is identical whether local or remote:

- Commands read from `.impl/issue.json` (same path in both environments)
- Progress tracking writes to `.impl/progress.md` (same path)
- Plan is in `.impl/plan.md` (same path)

## Why Two Folders?

**Visibility vs Privacy:**

- `.worker-impl/` is committed to make the plan visible in the PR before implementation starts
- `.impl/` is local to keep implementation state private

**Lifecycle Separation:**

- `.worker-impl/` has a PR lifecycle (created → visible → deleted after success)
- `.impl/` has an implementation lifecycle (created → used during impl → left for review)

**Command Consistency:**

- Commands always read from `.impl/` (same path local and remote)
- Remote workflow copies `.worker-impl/` to `.impl/` to ensure consistency

## Common Patterns

### Remote Implementation

1. `erk submit` creates `.worker-impl/` and commits it
2. GitHub Actions workflow copies `.worker-impl/` to `.impl/`
3. Implementation agent reads from `.impl/`
4. After success, workflow deletes `.worker-impl/` and commits cleanup

### Local Implementation

1. `erk wt create --from-issue N` creates `.impl/` directly
2. Implementation agent reads from `.impl/`
3. User manually deletes `.impl/` when done

## Directory Structure

```
repo-root/
├── .impl/              # Local implementation (gitignored)
│   ├── plan.md
│   ├── issue.json
│   ├── progress.md
│   ├── README.md
│   └── run-info.json
│
└── .worker-impl/       # Remote implementation (committed)
    ├── plan.md
    ├── issue.json
    ├── progress.md
    └── README.md
```

## Related Documentation

- [PR Finalization Paths](pr-finalization-paths.md) - How issue references flow to PR bodies
- [Issue Reference Flow](issue-reference-flow.md) - How `issue.json` is created and consumed
