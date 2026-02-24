# Documentation Plan: Add erk-slack-bot package for Slack command integration

## Context

This plan captures learnings from implementing `erk-slack-bot`, a new standalone package that enables Slack command integration for erk workflows. The implementation introduced a Socket Mode Slack bot that responds to mentions, executes erk commands (`plan list` and `one-shot`), and streams real-time progress updates back to Slack channels.

The implementation revealed several cross-cutting patterns and important clarifications needed in existing documentation. Most notably, the LBYL principle requires explicit boundary documentation to distinguish Python-internal operations from external API calls, and workspace dependency management requires coordination across multiple pyproject.toml files. The bot also established new patterns for streaming subprocess execution, message update fallback handling, and security-conscious subprocess argument passing.

Future agents working on integrations, subprocess execution, or multi-package workspaces will benefit from documented patterns around LBYL queue handling, shell=False safety, Slack API throttling, and workspace dependency version alignment. Without these docs, agents will repeat the same mistakes: using `queue.get(timeout=...)` with try/except, missing version conflicts in workspace packages, or flagging legitimate external API exception handling as EAFP violations.

## Raw Materials

PR #8003 implementation sessions and diff analysis

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 30 |
| Contradictions to resolve | 2 |
| Tripwire candidates (score>=4) | 8 |
| Potential tripwires (score 2-3) | 6 |

## Contradiction Resolutions

Resolve these BEFORE creating new documentation:

### 1. LBYL vs EAFP External API Boundary

**Existing doc:** `dignified-python` skill
**Conflict:** The current LBYL documentation doesn't distinguish between Python-internal operations (where you can check state before acting) and external API calls (Slack SDK, GitHub API, REST APIs) where exceptions are the only error signaling mechanism. This caused 5+ false positives in automated review, with the bot flagging legitimate exception handling as EAFP violations.
**Resolution:** UPDATE the dignified-python skill to add an explicit exception list:
- LBYL applies to: dict key checks, file existence, attribute checks, queue operations (with single producer/consumer)
- LBYL does NOT apply to: External REST APIs, third-party SDK calls (Slack, GitHub, AWS), database operations, network operations
- Key distinction: If you can check state before acting, use LBYL. If the only way to know is to try it, exceptions are acceptable.

### 2. Subprocess Error Handler After which() Guard

**Existing doc:** `docs/learned/architecture/subprocess-wrappers.md`
**Conflict:** The review bot correctly flagged a `FileNotFoundError` handler as dead code because a `which("uv")` LBYL guard made it unreachable. The existing documentation doesn't warn about this common mistake pattern.
**Resolution:** UPDATE subprocess-wrappers.md to add a "Common Mistakes" section showing:
- After a `which()` guard returns early on missing command, subsequent `FileNotFoundError` handlers are unreachable dead code
- Only handle runtime errors (TimeoutExpired, non-zero exit codes) after LBYL existence check

## Stale Documentation Cleanup

No stale documentation identified. All referenced existing docs have valid file paths.

## Documentation Items

### HIGH Priority

#### 1. LBYL External API Boundary Exception

**Location:** `.claude/skills/dignified-python/` (skill file)
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
## LBYL External API Boundary

LBYL applies to Python-internal operations where you can check state before acting:
- Dict key checks: `if key in d:` before `d[key]`
- File existence: `if path.exists():` before `path.read_text()`
- Attribute checks: `if hasattr(obj, "attr"):` before `obj.attr`
- Queue operations (single producer/consumer): `if not queue.empty():` before `queue.get_nowait()`

LBYL does NOT apply to external API calls where exceptions are the only error signaling:
- REST API calls (requests, httpx)
- Third-party SDK calls (Slack SDK, GitHub API, AWS boto3)
- Database operations
- Network socket operations

**Key distinction:** If you can check state before acting, use LBYL. If the only way to know outcome is to try the operation, exception handling is acceptable.

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py` for examples of acceptable exception handling around Slack API calls.
```

---

#### 2. Subprocess Dead Code After which() Guard

**Location:** `docs/learned/architecture/subprocess-wrappers.md`
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

Add to existing doc under new "Common Mistakes" section:

```markdown
## Common Mistakes

### Dead Code After LBYL Guard

When you add a `which()` check before subprocess execution, subsequent `FileNotFoundError` handlers become unreachable dead code:

**WRONG - Dead code after which() guard:**
```python
if which("command") is None:
    return Error("not found")
try:
    subprocess.run(["command"])
except FileNotFoundError:  # Unreachable! which() already handled this
    return Error("not found")
```

**CORRECT - Only handle runtime errors after LBYL guard:**
```python
if which("command") is None:
    return Error("not found")
try:
    subprocess.run(["command"], timeout=30)
except TimeoutExpired:
    return Error("timeout")
```

The LBYL check (`which()`) eliminates the file-not-found case, so only handle errors that can occur at runtime (timeouts, non-zero exit codes).
```

---

#### 3. LBYL Queue Pattern for Single Producer/Consumer

**Location:** `.claude/skills/dignified-python/` (skill file)
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
## Queue LBYL Pattern

For single-producer/single-consumer queue scenarios, use LBYL check before get:

**WRONG - EAFP with timeout exception:**
```python
try:
    item = queue.get(timeout=0.1)
except Empty:
    continue
```

**CORRECT - LBYL check before get:**
```python
if not queue.empty():
    item = queue.get_nowait()
```

**Important:** This LBYL pattern is ONLY safe for single-producer/single-consumer scenarios. For multi-threaded access from multiple consumers, the race window between `empty()` and `get_nowait()` requires different handling.

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py` for the streaming subprocess pattern using this approach.
```

---

#### 4. Standalone Package Exemption Taxonomy

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

Add section documenting package categories:

```markdown
## Package Taxonomy

Erk uses a multi-package workspace with different rule sets:

### Core erk (`src/erk/`)
All erk coding standards apply:
- LBYL everywhere
- Frozen dataclasses only
- Gateway ABC pattern
- Time abstraction via TimeProvider

### Standalone Applications (`packages/erk-slack-bot/`, `packages/erk-dev/`)
Most erk standards apply, with exemptions:
- Time abstraction NOT required (direct `time.time()` acceptable)
- May use third-party patterns (Pydantic Settings, slack-bolt decorators)
- LBYL still applies for Python-internal operations
- Security patterns required (shell=False for subprocess)

### Test Code (`tests/`)
Testing-specific rules:
- Fakes over mocks (fake-driven-testing skill)
- Test isolation requirements
- May use fixtures with different lifecycle

The taxonomy helps agents understand which rules apply in which contexts. When adding new packages, document their category explicitly.
```

---

#### 5. Subprocess Shell=False Safety

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8003]

**Draft Content:**

This is a tripwire candidate with score 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2). When agents write subprocess code with user input, they should be warned about shell injection risks.

The trigger is: Before calling subprocess.run or subprocess.Popen with user-supplied input.

The warning should convey: Always use shell=False with args as list, never shell=True with string concatenation. User input must never be shell-interpreted. Test with shell injection payloads like `fix this; rm -rf / && echo pwned`.

The target documentation is `docs/learned/architecture/subprocess-wrappers.md` which already covers subprocess patterns.

See `packages/erk-slack-bot/tests/test_runner.py` for shell injection test examples.

---

#### 6. Workspace Dependency Coordination

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

This is a tripwire candidate with score 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2). The implementation session encountered a dependency conflict where `uv lock --upgrade-package pydantic` failed because `erk-slack-bot` had `pydantic>=2.8.0,<2.9.0` conflicting with the main package's `pydantic>=2.10`.

The trigger is: Before upgrading dependencies with uv lock --upgrade-package.

The warning should convey: First grep all workspace pyproject.toml files for the package name and check for upper bounds (<X.Y.0) that might conflict. Update version constraints in all workspace packages BEFORE running uv lock.

This prevented a real failure during implementation. Agents need to coordinate version constraints across the entire workspace, not just the main package.

---

#### 7. PR Operations Skill Loading

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

This is a tripwire candidate with score 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1). The agent attempted `erk exec pr-thread resolve` which doesn't exist - the correct command is `erk exec resolve-review-thread`.

The trigger is: Before running erk exec commands for PR thread operations.

The warning should convey: Load pr-operations skill FIRST. It contains the canonical command reference. Common mistakes: `erk exec pr-thread resolve` (wrong), `erk exec resolve-review-thread` (correct).

The pr-operations skill contains the complete command reference. Without loading it, agents will guess wrong command names.

### MEDIUM Priority

#### 8. Slack Bot Architecture Overview

**Location:** `docs/learned/integrations/slack-bot-architecture.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - building Slack integrations for erk
  - working with slack-bolt or socket mode
  - understanding erk-slack-bot package structure
tripwires: 0
---

# Slack Bot Architecture

## Overview

The `erk-slack-bot` package provides Slack command integration for erk workflows. Users mention the bot with commands like `@erk plan list` or `@erk one-shot fix the tests` to execute erk operations directly from Slack.

## Package Structure

See `packages/erk-slack-bot/src/erk_slack_bot/` for the implementation:
- `app.py` - Slack app factory using slack-bolt
- `cli.py` - Entry point with Socket Mode handler
- `config.py` - Pydantic Settings configuration
- `models.py` - Discriminated union command types
- `parser.py` - Command parsing with mention stripping
- `runner.py` - Command execution (CliRunner and subprocess)
- `slack_handlers.py` - Event handlers with threading
- `utils.py` - Chunking, link extraction, resource loading

## Socket Mode Integration

The bot uses Socket Mode (not Events API webhooks) for simpler deployment. Socket Mode maintains a WebSocket connection to Slack, avoiding the need for a public webhook URL.

See `packages/erk-slack-bot/src/erk_slack_bot/cli.py` for Socket Mode handler initialization.

## Command Flow

1. User mentions bot: `@erk one-shot fix the login bug`
2. Parser strips mentions, normalizes case, identifies command type
3. Handler dispatches to appropriate runner (CliRunner for plan list, subprocess for one-shot)
4. Progress streams back via message updates or threaded replies
5. Final result posted with extracted PR/Run links

## Thread Safety

The bot uses daemon threads for fire-and-forget execution of long-running commands. The slack_sdk WebClient is thread-safe and can be passed to background threads.

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py` for threading patterns.
```

---

#### 9. Streaming Subprocess with LBYL Queue

**Location:** `docs/learned/integrations/streaming-subprocess.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - implementing streaming subprocess output
  - building real-time progress updates
  - using queues with LBYL pattern
tripwires: 2
---

# Streaming Subprocess Execution

## Overview

Pattern for streaming subprocess output line-by-line with LBYL queue communication between reader thread and main thread.

## Key Patterns

### LBYL Queue Communication

Use `queue.empty()` check before `get_nowait()` for single-producer/single-consumer scenarios:

```python
if not output_queue.empty():
    line = output_queue.get_nowait()
    on_line(line)
```

This follows erk's LBYL principle. Do NOT use `queue.get(timeout=...)` with try/except.

### Shell Injection Safety

Always pass subprocess arguments as a list with shell=False:

```python
subprocess.Popen(["uv", "run", "erk", "one-shot", user_message], shell=False)
```

Never use shell=True with string concatenation when user input is involved.

### Timeout Escalation

Implement graceful termination with SIGTERM followed by SIGKILL:

```python
process.terminate()  # SIGTERM
try:
    process.wait(timeout=5)
except TimeoutExpired:
    process.kill()  # SIGKILL
```

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py` for the complete streaming implementation.
```

---

#### 10. Slack Command Parsing with Discriminated Union

**Location:** `docs/learned/integrations/slack-command-parsing.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - parsing Slack commands
  - implementing discriminated union types with Pydantic
  - handling user input normalization
tripwires: 0
---

# Slack Command Parsing

## Overview

Pattern for type-safe command parsing using Pydantic discriminated unions with mention stripping and case normalization.

## Mention Stripping

Slack mentions come as `<@U123ABC>` tokens. Strip them before parsing:

```python
re.sub(r"<@[^>]+>", "", text).strip()
```

See `packages/erk-slack-bot/src/erk_slack_bot/parser.py` for implementation.

## Discriminated Union Commands

Use Pydantic Literal types for exhaustive command matching:

```python
class PlanListCommand(BaseModel):
    type: Literal["plan_list"] = "plan_list"

class OneShotCommand(BaseModel):
    type: Literal["one_shot"] = "one_shot"
    message: str

Command = PlanListCommand | OneShotCommand | ...
```

This enables type-safe exhaustive pattern matching in handlers.

See `packages/erk-slack-bot/src/erk_slack_bot/models.py` for command type definitions.

## Case Normalization

Normalize user input for flexible matching:
- `ONE-SHOT` matches `one-shot`
- `one shot` matches `one-shot` (hyphen flexibility)

See `packages/erk-slack-bot/src/erk_slack_bot/parser.py` for parsing logic.
```

---

#### 11. Slack Message Updates with Fallback

**Location:** `docs/learned/integrations/slack-message-updates.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - implementing live progress updates in Slack
  - handling Slack API errors gracefully
  - building real-time feedback UX
tripwires: 1
---

# Slack Message Updates with Fallback

## Overview

Pattern for live progress updates via `chat_update` with graceful degradation to threaded replies on API errors.

## Primary Update Pattern

Post an initial status message and update it in place:

```python
response = client.chat_postMessage(channel=channel, text="Starting...")
ts = extract_message_ts(response)
# Later:
client.chat_update(channel=channel, ts=ts, text="Progress: 50%")
```

## Graceful Degradation

If `chat_update` fails (message deleted, permissions changed), fall back to threaded replies:

```python
try:
    client.chat_update(channel=channel, ts=ts, text=progress)
except SlackApiError:
    if not fallback_posted:
        client.chat_postMessage(channel=channel, thread_ts=thread_ts,
                                text="Live updates unavailable, posting to thread")
        fallback_posted = True
    client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=progress)
```

Only post the fallback notice once.

## Update Throttling

Check time since last update to avoid rate limits:

```python
if time.time() - last_update_time < min_update_interval:
    return  # Skip this update
```

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py` for the complete implementation.
```

---

#### 12. PR Review Workflow Automation

**Location:** `docs/learned/pr-operations/pr-review-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - addressing PR review comments
  - using pr-preview-address or pr-address commands
  - resolving review threads in batch
tripwires: 1
---

# PR Review Workflow Automation

## Overview

Systematic workflow for addressing PR review feedback using erk commands and the pr-feedback-classifier skill.

## Workflow Steps

1. **Preview feedback**: Run `/erk:pr-preview-address` to classify and preview actionable items
2. **Select items**: Choose which feedback to address (local fixes vs discussion)
3. **Implement fixes**: Run `/erk:pr-address` to make changes
4. **Resolve threads**: Use `erk exec resolve-review-threads` with JSON stdin for batch resolution

## Batch Thread Resolution

Resolve multiple threads in a single operation:

```bash
echo '[{"thread_id": "PRRT_xxx", "comment": "Fixed"}]' | erk exec resolve-review-threads
```

This is more efficient than individual `erk exec resolve-review-thread` calls.

## Important

Load the `pr-operations` skill BEFORE running any PR thread commands. The skill contains the canonical command reference. Without it, agents guess wrong command names (e.g., `erk exec pr-thread resolve` which doesn't exist).
```

---

#### 13. Workspace Dependency Version Patterns

**Location:** `docs/learned/architecture/workspace-dependencies.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - adding dependencies to workspace packages
  - upgrading dependencies across the monorepo
  - resolving dependency conflicts
tripwires: 1
---

# Workspace Dependency Version Patterns

## Overview

Patterns for managing dependency versions across multiple pyproject.toml files in a uv workspace.

## Version Constraint Alignment

When adding a dependency that exists in other workspace packages, align version constraints:

1. Check main project's constraint: `grep pydantic pyproject.toml`
2. Check all workspace packages: `grep -r pydantic packages/*/pyproject.toml`
3. Use compatible constraints (avoid tight upper bounds like `<2.9.0`)

## Upgrade Coordination

Before running `uv lock --upgrade-package <pkg>`:

1. Search all pyproject.toml files for the package
2. Identify any upper bound constraints that would block the upgrade
3. Update constraints in ALL packages before running lock

Example failure: Main package wanted `pydantic>=2.10` but `erk-slack-bot` had `pydantic>=2.8.0,<2.9.0`. The upgrade failed until the upper bound was removed.

## Best Practice

Prefer open-ended constraints: `>=X.Y` without upper bounds when possible. This allows workspace-wide upgrades without coordination.
```

---

#### 14. Bot Review Lifecycle

**Location:** `docs/learned/ci/bot-review-lifecycle.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - understanding automated review bot comments
  - addressing review bot feedback
  - debugging false positives in automated reviews
tripwires: 0
---

# Bot Review Lifecycle

## Overview

Understanding the multi-iteration progression of automated review bots on PRs.

## Review Iterations

Review bots run on each push and create inline comments. The lifecycle:

1. **Initial review**: Bot scans diff, posts inline comments on potential issues
2. **Status update**: Bot posts summary comment with counts (violations, coverage, etc.)
3. **Subsequent reviews**: On new pushes, bot updates existing threads or creates new ones
4. **Resolution**: Agent or human resolves threads, bot updates status

## False Positive Detection

Bots can flag code that's actually correct. Common false positives:

- **LBYL external API boundary**: Bot flags exception handling on Slack/GitHub API calls as EAFP violation, but external APIs are exempt from LBYL
- **Dead code after LBYL guard**: Bot correctly identifies unreachable exception handlers (this is a TRUE positive, not false)

Before changing flagged code, verify the violation actually exists by reading the code in context.

## Test Coverage Metrics

Bots report test balance metrics. When flagged for low coverage:
- Check if files are "thin wrappers/config/types" (may be exempted)
- Consider whether the code is actually tested indirectly
- Create a plan for test additions if coverage is legitimately needed
```

---

#### 15. StrEnum Modernization Pattern

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

Add example to conventions.md:

```markdown
## StrEnum (Python 3.11+)

Use `StrEnum` instead of the old `(str, Enum)` pattern:

**Old pattern (pre-3.11):**
```python
class ConfigLevel(str, Enum):
    PROJECT = "project"
    USER = "user"
```

**Modern pattern (3.11+):**
```python
from enum import StrEnum

class ConfigLevel(StrEnum):
    PROJECT = "project"
    USER = "user"
```

StrEnum provides the same behavior with cleaner inheritance. Since erk requires Python 3.10+, use StrEnum for new code.

See `packages/erk-shared/src/erk_shared/config/schema.py` for example.
```

---

#### 16. subprocess.run Graceful Degradation Reference

**Location:** `docs/learned/architecture/subprocess-wrappers.md`
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

Add "Reference Implementations" section:

```markdown
## Reference Implementations

Standalone applications may use `subprocess.run` directly (gateway pattern exempt). When doing so, follow these patterns:

### Timeout Handling
```python
try:
    result = subprocess.run(args, timeout=30, capture_output=True)
except TimeoutExpired:
    return Error("command timed out")
```

### Missing Command Check (LBYL)
```python
if which("command") is None:
    return Error("command not found")
subprocess.run(["command", ...])  # No FileNotFoundError handler needed
```

### Exit Code Handling
```python
result = subprocess.run(args, capture_output=True)
if result.returncode != 0:
    return Error(f"command failed: {result.stderr.decode()}")
```

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py` for standalone application examples.
```

---

#### 17. Thin Wrapper Testing Deferral Policy

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #8003]

**Draft Content:**

Add section on test deferral:

```markdown
## Test Deferral Policy

Some files may be excluded from coverage requirements:

### Thin Wrappers
Files that are pure delegation with no logic (e.g., CLI entry points that just call other functions) may be deferred.

### Configuration/Settings
Pydantic Settings classes with no custom validators are often tested implicitly through integration tests.

### Type Definitions
Pure type definitions (Literal types, TypedDict, Protocol) don't need unit tests.

When review bots flag these files for low coverage, evaluate whether:
1. The file contains testable logic (add tests)
2. The file is a thin wrapper (note in PR, may be exempted)
3. Testing would provide value (create plan for later)

Document the rationale when deferring test coverage.
```

---

#### 18. Shell Injection Test Pattern

**Location:** `docs/learned/testing/subprocess-safety.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for subprocess execution
  - verifying shell injection safety
  - testing user input handling
tripwires: 1
---

# Subprocess Safety Testing

## Overview

Patterns for testing that subprocess calls are safe from shell injection.

## Shell Injection Test Payloads

Include malicious payloads in tests to verify shell=False protection:

```python
def test_safe_subprocess_args():
    # Payload that would execute rm if shell=True
    malicious_input = "fix this; rm -rf / && echo pwned"

    with patch("subprocess.Popen") as mock_popen:
        run_command(malicious_input)

        # Verify shell=False
        assert mock_popen.call_args.kwargs.get("shell") is False

        # Verify args as list (not string)
        args = mock_popen.call_args.args[0]
        assert isinstance(args, list)

        # Verify malicious input passed as single argument
        assert malicious_input in args
```

## Key Assertions

1. `shell=False` is explicitly set (or omitted, defaulting to False)
2. Arguments are passed as a list, not a string
3. User input is a single list element, not interpolated into a command string

See `packages/erk-slack-bot/tests/test_runner.py` for complete examples.
```

---

#### 19. Fake Pattern for Decorator-Based Registration

**Location:** `docs/learned/testing/slack-app-fakes.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - testing Slack app handlers
  - creating fakes for decorator-based APIs
  - testing event registration patterns
tripwires: 0
---

# Slack App Fakes

## Overview

Pattern for testing decorator-based handler registration (like slack-bolt) using custom Fake classes instead of MagicMock.

## FakeApp Pattern

Create a fake that records registered handlers:

```python
class FakeApp:
    def __init__(self):
        self.event_handlers: dict[str, list[Callable]] = {}
        self.message_handlers: list[Callable] = []

    def event(self, event_type: str):
        def decorator(fn):
            self.event_handlers.setdefault(event_type, []).append(fn)
            return fn
        return decorator

    def message(self, pattern: str = ""):
        def decorator(fn):
            self.message_handlers.append(fn)
            return fn
        return decorator
```

## Why Fakes Over Mocks

For decorator-based APIs, MagicMock doesn't capture the registration pattern correctly. A custom Fake:
- Records which handlers were registered
- Allows testing registration and invocation separately
- Provides explicit API matching the real object

See `packages/erk-slack-bot/tests/test_slack_handlers.py` for the complete FakeApp implementation.
```

---

#### 20. Slack Async Execution with Threading

**Location:** `docs/learned/integrations/slack-async-execution.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - running long operations from Slack handlers
  - using threading with Slack SDK
  - implementing fire-and-forget patterns
tripwires: 0
---

# Async Execution with Threading

## Overview

Pattern for running long operations in background threads from Slack event handlers.

## Why Threading Not Asyncio

slack-bolt event handlers are synchronous functions. For long-running operations, spawn a daemon thread:

```python
thread = Thread(
    target=run_long_operation,
    kwargs={"client": client, "channel": channel, "thread_ts": thread_ts},
    daemon=True
)
thread.start()
```

## Thread Safety

The slack_sdk WebClient is thread-safe. You can pass it to background threads and make API calls without additional synchronization.

## Daemon Threads

Use `daemon=True` for fire-and-forget execution. Daemon threads are terminated when the main program exits, avoiding orphaned threads.

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py` for the threading pattern.
```

---

#### 21. Slack Code Block Chunking

**Location:** `docs/learned/integrations/slack-chunking.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - posting large outputs to Slack
  - handling Slack message size limits
  - implementing line-preserving chunking
tripwires: 0
---

# Slack Code Block Chunking

## Overview

Algorithm for chunking large outputs to fit Slack's message size limits while preserving line boundaries.

## Size Limits

Slack has a ~4000 character limit for messages. For code blocks with backticks, use a safety margin (e.g., 2800 characters).

## Line-by-Line Algorithm

1. Accumulate lines until adding the next line would exceed the limit
2. Emit the current chunk
3. Continue with the remaining lines
4. For single lines exceeding the limit, split at character boundaries

```python
def chunk_for_slack(text: str, max_chars: int = 2800) -> list[str]:
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > max_chars:
            if current:
                chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks
```

See `packages/erk-slack-bot/src/erk_slack_bot/utils.py` for the complete implementation.
```

---

#### 22. Link Extraction from Command Output

**Location:** `docs/learned/integrations/link-extraction.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - extracting URLs from command output
  - parsing structured CLI output
  - building summary messages from results
tripwires: 0
---

# Link Extraction from Command Output

## Overview

Pattern for extracting PR and workflow run URLs from erk command output.

## Regex Patterns

Match URLs on labeled lines:

```python
PR_URL_RE = re.compile(r"^PR:\s+(https://\S+)", re.MULTILINE)
RUN_URL_RE = re.compile(r"^Run:\s+(https://\S+)", re.MULTILINE)
```

## Early Termination

For efficiency, stop scanning once both URLs are found:

```python
pr_url = None
run_url = None
for line in output.splitlines():
    if pr_match := PR_URL_RE.match(line):
        pr_url = pr_match.group(1)
    if run_match := RUN_URL_RE.match(line):
        run_url = run_match.group(1)
    if pr_url and run_url:
        break
```

See `packages/erk-slack-bot/src/erk_slack_bot/utils.py` for the complete implementation.
```

---

#### 23. Slack Bot Configuration with Pydantic

**Location:** `docs/learned/integrations/slack-bot-config.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - configuring Slack bots
  - using Pydantic BaseSettings
  - handling environment variables and .env files
tripwires: 0
---

# Slack Bot Configuration

## Overview

Pattern for type-safe configuration using Pydantic BaseSettings with .env file support.

## Settings Class

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    slack_bot_token: str  # Required
    slack_app_token: str  # Required
    timeout_seconds: int = 300  # Optional with default
```

## Required vs Optional

- Required settings: No default value, must be in environment or .env
- Optional settings: Provide sensible defaults for development

## Field Aliases

Use `Field(alias="...")` when environment variable names differ from field names.

See `packages/erk-slack-bot/src/erk_slack_bot/config.py` for the complete Settings class.
```

### LOW Priority

#### 24. Click CliRunner In-Process Execution

**Location:** `docs/learned/integrations/click-in-process.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - executing Click commands programmatically
  - avoiding subprocess overhead for simple queries
  - testing CLI commands
tripwires: 0
---

# Click In-Process Execution

## Overview

Pattern for executing Click commands in-process using CliRunner, avoiding subprocess overhead.

## When to Use

- Fast, synchronous commands (like `erk plan list`)
- When you need structured access to output
- When subprocess overhead is unacceptable

## Basic Usage

```python
from click.testing import CliRunner
from erk.cli import cli

runner = CliRunner()
result = runner.invoke(cli, ["plan", "list", "--json"])
if result.exit_code == 0:
    data = json.loads(result.output)
```

## Limitations

- No streaming output (waits for completion)
- Shares process state (may have side effects)
- Not suitable for long-running commands

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py` for usage in the Slack bot.
```

---

#### 25. Read Acknowledgment with Emoji Reaction

**Location:** `docs/learned/integrations/slack-read-ack.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - providing immediate feedback in Slack
  - using emoji reactions for UX
  - handling reaction API errors
tripwires: 0
---

# Read Acknowledgment with Emoji Reaction

## Overview

UX pattern for acknowledging message receipt before long-running operations.

## Eyes Emoji Pattern

Add an eyes emoji reaction immediately to show the message was received:

```python
try:
    client.reactions_add(channel=channel, timestamp=ts, name="eyes")
except SlackApiError as e:
    # Ignore common non-fatal errors
    if e.response["error"] not in ("already_reacted", "missing_scope", "not_reactable"):
        raise
```

## Why This Pattern

- Provides immediate feedback (< 1 second)
- Non-blocking (operation continues regardless of reaction success)
- Familiar UX (users expect reactions as acknowledgment)

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py` for implementation.
```

---

#### 26. Resource Loading with importlib

**Location:** `docs/learned/integrations/resource-loading.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - loading packaged resources
  - accessing data files from installed packages
  - handling development vs installed resource paths
tripwires: 0
---

# Resource Loading with importlib

## Overview

Pattern for loading packaged resources using importlib.resources with fallback for development.

## Basic Pattern

```python
from importlib import resources
from importlib.util import find_spec
from pathlib import Path

def load_resource(package: str, filename: str) -> str:
    if find_spec(package):
        return resources.files(package).joinpath(filename).read_text()
    # Fallback for development
    return (Path(__file__).parent / "resources" / filename).read_text()
```

## Why Fallback

During development, the package may not be installed. The fallback uses `__file__` to locate resources relative to the source file.

See `packages/erk-slack-bot/src/erk_slack_bot/utils.py` for the complete implementation.
```

---

#### 27. Local Editable Development with Makefile

**Location:** `docs/learned/integrations/slack-bot-dev-workflow.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - developing standalone erk packages locally
  - testing erk changes without publishing
  - setting up development environments
tripwires: 0
---

# Local Editable Development

## Overview

Makefile pattern for detecting local erk checkout and using editable installs.

## ERK_LOCAL_PATH Detection

```makefile
ERK_LOCAL_PATH ?= $(shell test -d ../../src/erk && echo "../../")

dev:
ifdef ERK_LOCAL_PATH
    uv run --with-editable $(ERK_LOCAL_PATH) erk-slack-bot
else
    uv run erk-slack-bot
endif
```

## Usage

- If run from within the erk repo, automatically uses local erk source
- Override with `ERK_LOCAL_PATH=/path/to/erk make dev`
- Without local path, uses published erk from PyPI

See `packages/erk-slack-bot/Makefile` for the complete pattern.
```

---

#### 28. Plan Duplicate Detection Behavior

**Location:** `docs/learned/planning/plan-save-behavior.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - saving plans multiple times in a session
  - understanding plan-save idempotency
  - debugging plan creation issues
tripwires: 0
---

# Plan Save Duplicate Detection

## Overview

The `erk exec plan-save` command detects duplicate saves within a session.

## Behavior

When plan-save detects the session already saved a plan:

```json
{
  "skipped_duplicate": true,
  "plan_number": 8025,
  "branch_name": "plan/8025"
}
```

## Why This Matters

- Safe to retry plan-save (idempotent)
- Prevents accidental duplicate plan issues
- Session tracking enables detection

This is useful in iterative sessions where agents may invoke plan-save multiple times.
```

---

#### 29. Test Balance Metrics

**Location:** `docs/learned/testing/coverage-policy.md`
**Action:** CREATE
**Source:** [PR #8003]

**Draft Content:**

```markdown
---
read-when:
  - understanding test coverage bot reports
  - evaluating test balance metrics
  - responding to coverage feedback
tripwires: 0
---

# Test Coverage Policy

## Test Balance Metric

Review bots report test balance as a ratio of source files to test files.

## Interpreting Reports

- High balance: Many source files, few test files (add tests)
- Low balance: Good test coverage
- Exemptions: Thin wrappers, config, types may be excluded

## When Flagged

1. Check if file is exemptible (thin wrapper, pure config, type definitions)
2. Evaluate if testing provides value
3. Create plan for test additions or document exemption rationale

Not all flagged files need tests. Use judgment based on the file's purpose and complexity.
```

---

#### 30. Subprocess Timeout Escalation

**Location:** `docs/learned/integrations/streaming-subprocess.md`
**Action:** UPDATE (merge into existing item #9)
**Source:** [PR #8003]

**Draft Content:**

This content should be merged into the streaming-subprocess.md document created in item #9. Add a section on timeout escalation:

```markdown
## Timeout Escalation

For graceful termination of long-running subprocesses:

1. Send SIGTERM first: `process.terminate()`
2. Wait briefly: `process.wait(timeout=5)`
3. Force kill if needed: `process.kill()`

This allows the process to clean up before force termination.

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py` for the escalation pattern.
```

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Wrong PR Thread Command Syntax

**What happened:** Agent attempted `erk exec pr-thread resolve PRRT_xxx` which doesn't exist
**Root cause:** Agent guessed command name without checking documentation
**Prevention:** Always load `pr-operations` skill before PR thread operations
**Recommendation:** TRIPWIRE (added above)

### 2. Workspace Dependency Resolution Failure

**What happened:** `uv lock --upgrade-package pydantic` failed with version conflict
**Root cause:** `erk-slack-bot` had tight upper bound `pydantic>=2.8.0,<2.9.0` conflicting with main package's `pydantic>=2.10`
**Prevention:** Before upgrading, grep all workspace pyproject.toml for the package and check for conflicting constraints
**Recommendation:** TRIPWIRE (added above)

### 3. Unnecessary Code Changes for False Positives

**What happened:** Bot flagged exception handling that was actually acceptable (external API calls)
**Root cause:** LBYL documentation didn't clearly define external API boundary
**Prevention:** Verify bot flags are true violations before making changes
**Recommendation:** ADD_TO_DOC (LBYL external API boundary update)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Workspace Dependency Upgrade Coordination

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before upgrading dependencies with `uv lock --upgrade-package`
**Warning:** First grep all workspace pyproject.toml files for the package name and check for upper bounds (<X.Y.0) that might conflict. Update version constraints in all workspace packages BEFORE running uv lock.
**Target doc:** `docs/learned/architecture/tripwires.md`

This caused a real upgrade failure during implementation. The main package wanted pydantic 2.10+, but erk-slack-bot had a tight <2.9.0 bound that blocked the upgrade.

### 2. PR Operations Skill Loading

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before running erk exec commands for PR thread operations
**Warning:** Load pr-operations skill FIRST. It contains the canonical command reference. Common mistakes: `erk exec pr-thread resolve` (wrong), `erk exec resolve-review-thread` (correct).
**Target doc:** `docs/learned/pr-operations/tripwires.md`

Without the skill loaded, agents will guess wrong command names and waste time on failed attempts.

### 3. Subprocess Shell=False Safety

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before calling subprocess.run or subprocess.Popen with user input
**Warning:** ALWAYS use shell=False with args as list, NEVER shell=True with string concatenation. User input must never be shell-interpreted. Test with shell injection payloads.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is critical for the Slack bot where user messages flow directly to subprocess execution.

### 4. LBYL External API Boundary

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before flagging exception handling as EAFP violation
**Warning:** LBYL applies to Python-internal operations (dict, file, attributes). External API calls (Slack SDK, GitHub API, REST APIs, databases) that raise exceptions are EXEMPT. If you can't check state before acting, exceptions are acceptable.
**Target doc:** `docs/learned/architecture/tripwires.md`

This clarification would have prevented 5+ false positives in the automated review.

### 5. Dead Code After which() Guard

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, Silent failure +2)
**Trigger:** After adding which() check before subprocess call
**Warning:** Remove any subsequent FileNotFoundError handler - it's dead code. After which() guard, only handle runtime errors (TimeoutExpired, non-zero exit codes).
**Target doc:** `docs/learned/architecture/tripwires.md`

The review bot correctly caught this, but it's a subtle issue that will recur.

### 6. Slack API Rate Limit Throttling

**Score:** 5/10 (Non-obvious +2, External tool quirk +1, Cross-cutting +2)
**Trigger:** Before calling Slack API in a loop (chat_update, post_message)
**Warning:** Throttle updates: check time since last API call to avoid rate limits. Use graceful degradation: try chat_update first, fall back to post_message on SlackApiError.
**Target doc:** `docs/learned/integrations/tripwires.md`

Rate limiting can cause silent failures or unexpected errors during progress updates.

### 7. LBYL Queue Pattern Thread Safety

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using Queue.get(timeout=...) with try/except in LBYL codebase
**Warning:** Use queue.empty() check followed by get_nowait() instead. ONLY safe for single-producer/single-consumer. For multi-threaded scenarios, verify thread safety requirements.
**Target doc:** `docs/learned/architecture/tripwires.md`

This applies the LBYL principle to Queue objects, which isn't immediately obvious.

### 8. Multi-Package Pydantic Version Alignment

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When creating new workspace package with pydantic dependency
**Warning:** Check main project's pydantic version constraint and align new package accordingly. Avoid tight upper bounds (<X.Y.0) that prevent workspace-wide upgrades. Use >=X.Y without upper bound if possible.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is a specific instance of the workspace dependency coordination issue.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Graceful Degradation on Slack API Errors

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Specific to Slack integration, not cross-cutting enough for general tripwire. Document in slack-message-updates.md instead.

### 2. Standalone Package Exemption Rules

**Score:** 3/10 (Non-obvious +2, Cross-cutting +2, minus not destructive)
**Notes:** Taxonomy is clear once documented. Low risk of harmful mistakes, just confusion about which rules apply.

### 3. Thin Wrapper Test Deferral Policy

**Score:** 2/10 (Non-obvious +2)
**Notes:** Policy decision, not technical gotcha. Document in testing.md to clarify expectations.

### 4. Test Balance Metrics Interpretation

**Score:** 2/10 (Non-obvious +2)
**Notes:** Informational, not a footgun. Document but don't tripwire.

### 5. Plan Duplicate Detection Behavior

**Score:** 2/10 (Non-obvious +2)
**Notes:** Safe behavior (idempotent). Surprising but not harmful.

### 6. StrEnum Modernization Pattern

**Score:** 2/10 (Non-obvious +2)
**Notes:** Convention improvement, not critical. Document in conventions.md.
