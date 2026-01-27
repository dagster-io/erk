---
title: Uncategorized Tripwires
read_when:
  - "working on uncategorized code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from uncategorized/*.md frontmatter -->

# Uncategorized Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding --force flag to a CLI command** → Read [Code Conventions](conventions.md) first. Always include -f as the short form. Pattern: @click.option("-f", "--force", ...)

**CRITICAL: Before adding a function with 5+ parameters** → Read [Code Conventions](conventions.md) first. Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures and Click command callbacks.

**CRITICAL: Before adding a new method to Git/GitHub/Graphite ABC** → Read [Universal Tripwires](universal-tripwires.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding file I/O or subprocess calls to class `__init__`** → Read [Universal Tripwires](universal-tripwires.md) first. Keep `__init__` lightweight; use factory methods like `from_config_path()`.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Universal Tripwires](universal-tripwires.md) first. After os.chdir(), regenerate context using regenerate_context().

**CRITICAL: Before importing time module or calling time.sleep()/datetime.now()** → Read [Universal Tripwires](universal-tripwires.md) first. Use context.time.sleep() and context.time.now() for testability.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Universal Tripwires](universal-tripwires.md) first. Bug fixes require regression tests.

**CRITICAL: Before parsing objective roadmap PR column status** → Read [Erk Glossary](glossary.md) first. PR column format is non-standard: empty=pending, #XXXX=done (merged PR), `plan #XXXX`=plan in progress. This is erk-specific, not GitHub convention.

**CRITICAL: Before raising exceptions for expected failure cases** → Read [Universal Tripwires](universal-tripwires.md) first. Use discriminated unions (T | ErrorType) instead.

**CRITICAL: Before using Path.home() directly in production code** → Read [Universal Tripwires](universal-tripwires.md) first. Use gateway abstractions instead (ClaudeInstallation, ErkInstallation).

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Universal Tripwires](universal-tripwires.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI).

**CRITICAL: Before using gh pr diff --name-only in production code** → Read [Universal Tripwires](universal-tripwires.md) first. For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead. See github-cli-limits.md.

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.
