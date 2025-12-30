---
title: Generated Tripwires
read_when:
  - "checking tripwire rules"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Tripwires

Action-triggered rules that fire when you're about to perform specific actions.

**CRITICAL: Before passing dry_run boolean flags through function parameters** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use dependency injection with DryRunGit/DryRunGitHub wrappers instead of boolean flags.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError.

**CRITICAL: Before importing time module or calling time.sleep()** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use context.time.sleep() for testability. Direct time.sleep() makes tests slow.

**CRITICAL: Before implementing CLI flags that affect post-mutation behavior** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk pr land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target).

**CRITICAL: Before editing docs/agent/index.md or docs/agent/tripwires.md directly** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. These are generated files. Edit the source frontmatter instead, then run 'dot-agent docs sync'.

**CRITICAL: Before comparing worktree path to repo_root to detect root worktree** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use WorktreeInfo.is_root instead of path comparison. Path comparison fails when running from within a non-root worktree because ctx.cwd resolves differently.

**CRITICAL: Before adding a new method to Git ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to GitHub ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to Graphite ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before passing variables to gh api graphql as JSON blob** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work.

**CRITICAL: Before passing array or object variables to gh api graphql with -F and json.dumps()** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values.

**CRITICAL: Before checking if get_pr_for_branch() returned a PR** → Read [Not-Found Sentinel Pattern](architecture/not-found-sentinel.md) first. Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](architecture/protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](architecture/subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI).

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.

**CRITICAL: Before running gt sync or gt repo sync on user's behalf** → Read [Auto-Restack Command Usage](erk/auto-restack.md) first. NEVER run 'gt sync' or 'gt repo sync' automatically. This command synchronizes all Graphite branches with GitHub and can delete branches, modify stack relationships, and make irreversible changes. The user must run this command explicitly.

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](planning/scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](planning/scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](sessions/parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.
