# Plan: Preserve Thinking Blocks and Metadata in Session Preprocessor

## Problem

The session preprocessor (`preprocess_session.py`) silently drops several content types from raw JSONL session logs. Most critically, `thinking` blocks from Opus models are lost — these contain reasoning that's essential for doc generation decisions.

## Changes

### File: `src/erk/cli/commands/exec/scripts/preprocess_session.py`

**1. Add `<thinking>` XML element for thinking blocks (lines 460-476)**

In `generate_compressed_xml`, add an `elif` branch for `thinking` blocks in the assistant content loop:

```python
elif content.get("type") == "thinking":
    thinking_text = content.get("thinking", "")
    if thinking_text.strip():
        xml_lines.append(f"  <thinking>{escape_xml(thinking_text)}</thinking>")
```

**2. Add `<summary>` XML element for summary entries (line 403 area)**

In the main entry loop, add a handler for `summary` entry type:

```python
elif entry_type == "summary":
    summary_text = message.get("summary", entry.get("summary", ""))
    if summary_text:
        xml_lines.append(f"  <summary>{escape_xml(str(summary_text))}</summary>")
```

Note: `summary` entries store the summary directly on the entry, not inside `message`. Need to check both locations.

**3. Add `<system>` XML element for system entries (line 403 area)**

In the main entry loop, add a handler for `system` entry type:

```python
elif entry_type == "system":
    subtype = entry.get("subtype", "")
    duration_ms = entry.get("durationMs", "")
    xml_lines.append(f'  <system subtype="{escape_xml(str(subtype))}" duration_ms="{escape_xml(str(duration_ms))}" />')
```

**4. Preserve `usage` metadata on assistant entries**

Currently line 563 explicitly deletes usage. Remove that deletion. In `generate_compressed_xml`, emit usage as an attribute on `<assistant>` or as a separate element. Simplest approach — add as attribute on the first `<assistant>` text block or as a standalone `<usage>` element:

```python
# In the assistant handler, after processing content blocks:
usage = message.get("usage", {})
if usage:
    parts = [f'{k}="{v}"' for k, v in usage.items()]
    xml_lines.append(f'  <usage {" ".join(parts)} />')
```

Also remove the `del filtered["message"]["usage"]` at line 563 in `process_log_file`.

**5. Preserve `model` field on assistant entries**

In `process_log_file`, preserve the `model` field alongside `gitBranch`:

```python
if "model" in entry.get("message", {}):
    filtered["model"] = entry["message"]["model"]
```

In `generate_compressed_xml`, emit model as metadata on assistant entries or as a `<meta>` element (once, like gitBranch).

### File: `tests/unit/cli/commands/exec/scripts/fixtures.py`

Add new fixtures:

- `JSONL_ASSISTANT_WITH_THINKING` — assistant message with `thinking` + `text` blocks
- `JSONL_SUMMARY_ENTRY` — summary entry type
- `JSONL_SYSTEM_ENTRY` — system entry with `turn_duration` subtype
- `JSONL_ASSISTANT_WITH_USAGE` — assistant with usage metadata (update existing fixture or add new)

### File: `tests/unit/cli/commands/exec/scripts/test_preprocess_session.py`

Add tests:

- `test_generate_xml_assistant_thinking_block` — thinking block emits `<thinking>` XML
- `test_generate_xml_assistant_thinking_and_text` — both thinking and text preserved
- `test_generate_xml_empty_thinking_block_skipped` — empty thinking blocks are not emitted
- `test_generate_xml_summary_entry` — summary entries emit `<summary>` XML
- `test_generate_xml_system_entry` — system entries emit `<system>` XML
- `test_process_log_file_preserves_usage` — usage metadata no longer stripped
- `test_generate_xml_usage_metadata` — usage data emitted in XML

Update existing test:
- `test_process_log_file_removes_usage_field` — invert or remove, since usage is now preserved

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_preprocess_session.py -v`
2. Run integration tests: `uv run pytest tests/integration/cli/commands/exec/scripts/ -v`
3. Manual verification: run `erk exec preprocess-session --stdout` on a real session JSONL that contains thinking blocks (e.g., an Opus session) and confirm `<thinking>` elements appear in output
4. Run ty/ruff: `uv run ruff check src/erk/cli/commands/exec/scripts/preprocess_session.py` and `uv run ty check src/erk/cli/commands/exec/scripts/preprocess_session.py`