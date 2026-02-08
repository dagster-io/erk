---
title: LiveDisplay Gateway
read_when:
  - "implementing live-updating terminal displays"
  - "working with TUI real-time updates"
  - "showing progress indicators"
tripwires:
  - "LiveDisplay is primarily used in watch loops — guard with try/finally to ensure stop() is called even on KeyboardInterrupt"
  - "RealLiveDisplay writes to stderr by default (matches erk's user_output convention) — stdout is reserved for structured data"
---

# LiveDisplay Gateway

## Why This Gateway Exists

Rich's `Live` display requires careful lifecycle management (start → update loop → stop) and creates test challenges: you can't assert on live-updating terminal output without capturing it. The gateway solves this by:

1. **Encapsulating lifecycle complexity**: Forces start/stop pairing through interface contract
2. **Test capture**: `FakeLiveDisplay` records all updates for assertions without terminal I/O
3. **stderr convention**: Aligns with erk's stdout/stderr split (user output on stderr, structured data on stdout)

## Cross-Cutting Pattern: Watch Loop Architecture

<!-- Source: src/erk/cli/commands/plan/list_cmd.py, _run_watch_loop -->

The canonical usage pattern appears in `_run_watch_loop()` at `src/erk/cli/commands/plan/list_cmd.py:578-629`. This demonstrates the ONLY correct way to use LiveDisplay:

1. **Start once** before entering the loop
2. **Update repeatedly** inside the loop (every tick)
3. **Stop in finally block** to guarantee cleanup on KeyboardInterrupt

The finally block is critical: watch loops intentionally run until Ctrl+C, so stop() MUST execute in the finally clause to restore normal terminal mode.

## Anti-Pattern: Missing finally Block

**WRONG**:
```python
display.start()
while True:
    display.update(content)
    time.sleep(1.0)
display.stop()  # Never reached when user hits Ctrl+C
```

The stop() call never executes when KeyboardInterrupt fires. Terminal remains in live mode, breaking subsequent output.

**CORRECT**:
```python
display.start()
try:
    while True:
        display.update(content)
        time.sleep(1.0)
except KeyboardInterrupt:
    pass
finally:
    display.stop()  # Always executes
```

## Decision: Why stderr Instead of stdout

<!-- Source: packages/erk-shared/src/erk_shared/gateway/live_display/real.py, RealLiveDisplay.__init__ -->

`RealLiveDisplay.__init__()` hardcodes `stderr=True` in the Console constructor (line 13). This matches erk's convention:

- **stdout**: Machine-readable output (JSON, CSV, issue numbers for shell piping)
- **stderr**: Human-readable output (tables, progress indicators, error messages)

Live displays are inherently human-readable (Rich tables, spinners, progress bars), so they must write to stderr. Writing to stdout would corrupt structured data that downstream tools pipe from erk commands.

## Fake Capabilities: What Tests Can Assert

<!-- Source: packages/erk-shared/src/erk_shared/gateway/live_display/fake.py, FakeLiveDisplay -->

`FakeLiveDisplay` provides two properties for test assertions:

- **`updates`**: List of all renderables passed to `update()`, in order
- **`is_active`**: Boolean tracking start/stop lifecycle state

The fake enables tests to verify:
- **Update frequency**: "Did we update the display after each step?"
- **Update content**: "Does the display show correct progress/status?"
- **Lifecycle correctness**: "Did we start before updating and stop at the end?"

Critically, the fake records the **actual renderable objects** (Rich Table, Panel, etc.), not strings. Tests can introspect Rich object properties (e.g., table rows, panel title) for precise assertions.

## When to Use vs Console Gateway

**Use LiveDisplay when**:
- Output updates repeatedly (watch loops, progress bars)
- User should see a single "slot" being rewritten, not scrolling output

**Use Console when**:
- Output is static (one-time table, message)
- Each call adds a new line (scrolling output)

The performance boundary: Starting/stopping LiveDisplay for a single update is wasteful overhead. If you only call update() once, just use Console.print() instead.

## Implementation Files

Standard 3-file gateway pattern:
- `packages/erk-shared/src/erk_shared/gateway/live_display/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/live_display/real.py`
- `packages/erk-shared/src/erk_shared/gateway/live_display/fake.py`

No types.py or factory.py — the interface is simple enough to not warrant them.

## Related Topics

- [Gateway Inventory](gateway-inventory.md) — Discovering all available gateways
- [Console Gateway](gateway-inventory.md) — For static output
- [Textual Framework](../textual/) — For full TUI applications
