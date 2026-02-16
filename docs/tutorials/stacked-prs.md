# Stacked PRs with Graphite

An optional enhancement that enables stacked pull requests for incremental feature development.

## Do You Need This?

**No.** Erk works out-of-the-box without Graphite.

Without Graphite, each feature branch is independent. You create a branch, make changes, and submit a PR. When the PR merges, you're done.

With Graphite, branches stack on each other. Each branch builds on its parent, creating a chain of dependent PRs that reviewers can examine incrementally.

| Behavior         | Without Graphite       | With Graphite                |
| ---------------- | ---------------------- | ---------------------------- |
| Branch model     | Independent branches   | Linear stacks                |
| PR relationships | Manual tracking        | Automatic parent-child       |
| After landing    | Branches stay separate | Upstack branches auto-rebase |
| Navigation       | `git checkout`         | `erk up` / `erk down`        |

## When to Consider Graphite

You might want Graphite if you:

- Build features incrementally (multiple dependent PRs)
- Want reviewers to see logical progression
- Like automatic rebasing when base PR lands
- Work on large features that benefit from staged reviews

You probably don't need it if you:

- Work on independent features
- Prefer simple single-PR workflow
- Are just getting started with erk

## Setup

### 1. Install Graphite CLI

```bash
npm install -g @withgraphite/graphite-cli
```

### 2. Authenticate with GitHub

```bash
gt auth
```

### 3. Enable in Erk

```bash
erk config set use_graphite true
```

### 4. Initialize in Your Repository

```bash
gt init
```

This creates Graphite metadata in your repository's `.git` directory.

## Verification

After setup, verify everything is working:

```bash
# Check Graphite version
gt --version

# Check erk sees Graphite
erk doctor
```

You should see Graphite listed as available in the doctor output.

## Mental Model

**Critical concept:** Visualize trunk at the BOTTOM.

```
TOP      feat-3  <- upstack (leaf)
         feat-2
         feat-1
BOTTOM   main    <- downstack (trunk)
```

- **UPSTACK** = away from trunk (toward leaves/top)
- **DOWNSTACK** = toward trunk (toward main/bottom)

This visualization matters because:

- `erk up` moves away from main (toward the top)
- `erk down` moves toward main (toward the bottom)
- PRs land from bottom to top (main first, then each layer up)

## Key Erk Commands with Graphite

| Command          | Purpose                             |
| ---------------- | ----------------------------------- |
| `erk up`         | Move to upstack (child) worktree    |
| `erk down`       | Move to downstack (parent) worktree |
| `erk stack list` | Visualize your stack                |
| `erk pr land`    | Land current PR and navigate        |

When Graphite is enabled, `erk implement` automatically tracks new branches in the stack.

## Your First Stack

After completing the [First Plan](first-plan.md) tutorial, try building stacked changes:

### 1. Start from a Clean State

```bash
erk wt checkout root
gt sync
```

### 2. Create Your First Stacked Branch

```bash
gt create feature-part-1 -m "Add data model"
# ... make changes ...
git add .
gt modify -m "Add data model"
```

### 3. Stack Another Branch on Top

```bash
gt create feature-part-2 -m "Add API endpoints"
# ... make changes ...
git add .
gt modify -m "Add API endpoints"
```

### 4. Submit the Stack

```bash
gt submit --stack
```

This creates two PRs: one for `feature-part-1` (based on main) and one for `feature-part-2` (based on `feature-part-1`).

### 5. Navigate Your Stack

```bash
# See the stack structure
erk stack list

# Move down toward main
erk down

# Move back up
erk up
```

## Troubleshooting

### Branch not tracked by Graphite

If a branch exists but isn't in the stack:

```bash
gt track --parent <parent-branch>
```

### Stack out of sync

If changes on GitHub aren't reflected locally:

```bash
gt sync
```

Or through erk:

```bash
erk pr sync
```

### "No stack found" error

Make sure you've initialized Graphite in the repository:

```bash
gt init
```

And that you're on a tracked branch (not main/trunk).

## See Also

- [Stacked PRs](../topics/stacked-prs.md) - Conceptual understanding of stacked PRs
- [Graphite Issues](../faq/graphite-issues.md) - Detailed troubleshooting
- [Shell Integration](shell-integration.md) - Another optional enhancement
