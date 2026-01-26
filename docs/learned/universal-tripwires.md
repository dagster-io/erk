---
title: Universal Tripwires
read_when:
  - "starting any coding task"
  - "writing new code in erk"
tripwires:
  - action: "using bare subprocess.run with check=True"
    warning: "Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI)."
  - action: "adding a new method to Git/GitHub/Graphite ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
  - action: "raising exceptions for expected failure cases"
    warning: "Use discriminated unions (T | ErrorType) instead."
  - action: "using Path.home() directly in production code"
    warning: "Use gateway abstractions instead (ClaudeInstallation, ErkInstallation)."
  - action: "calling os.chdir() in erk code"
    warning: "After os.chdir(), regenerate context using regenerate_context()."
  - action: "importing time module or calling time.sleep()/datetime.now()"
    warning: "Use context.time.sleep() and context.time.now() for testability."
  - action: "adding file I/O or subprocess calls to class `__init__`"
    warning: "Keep `__init__` lightweight; use factory methods like `from_config_path()`."
  - action: "modifying business logic in src/ without adding a test"
    warning: "Bug fixes require regression tests."
  - action: "using gh pr diff --name-only in production code"
    warning: "For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead. See github-cli-limits.md."
---

# Universal Tripwires

These critical rules apply across **all** code areas in erk. They are the most important tripwires that every agent should be aware of before writing any code.

Unlike category-specific tripwires (which are loaded when working in specific directories), universal tripwires should always be consulted.

## Related Documentation

Each tripwire links to detailed documentation:

- [Subprocess Wrappers](architecture/subprocess-wrappers.md) - Wrapper functions for subprocess calls
- [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) - 5-place implementation pattern
- [Discriminated Union Error Handling](architecture/discriminated-union-error-handling.md) - Error handling patterns
- [Exec Script Testing Patterns](testing/exec-script-testing.md) - Path.home() alternatives
- [Erk Architecture Patterns](architecture/erk-architecture.md) - Context regeneration, time abstraction, lightweight init
- [Erk Test Reference](testing/testing.md) - Test requirements
- [GitHub CLI Limits](architecture/github-cli-limits.md) - gh pr diff size limits and REST API alternatives
