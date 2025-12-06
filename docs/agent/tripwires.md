---
title: Generated Tripwires
read_when:
  - "checking tripwire rules"
---

# Tripwires

Action-triggered rules that fire when you're about to perform specific actions.

**CRITICAL: Before passing dry_run boolean flags through function parameters** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use dependency injection with DryRunGit/DryRunGitHub wrappers instead of boolean flags.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError.

**CRITICAL: Before importing time module or calling time.sleep()** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use context.time.sleep() for testability. Direct time.sleep() makes tests slow.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](architecture/protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](architecture/subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (integration) or run_with_error_reporting() (CLI).

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](planning/scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](planning/scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](sessions/parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.
