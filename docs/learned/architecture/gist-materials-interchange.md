---
title: Gist Materials Interchange Format
read_when:
  - working with learn materials upload/download, debugging gist-based file transfer, implementing new file packing formats
last_audited: "2026-02-05 12:32 PT"
audit_result: edited
---

# Gist Materials Interchange Format

Erk uses GitHub Gists as a data carrier to transfer multiple files between the local machine and GitHub Actions CI environments. Files are packed into a single gist using a delimiter-based format.

## Why Gists as Data Carrier?

**Problem**: Async learn workflow needs to transfer session XML files, PR comments, and metadata from local machine to GitHub Actions codespace.

**Solution**: Pack all files into a single gist:

- Gist URL passed to GitHub Actions workflow via `workflow_dispatch` input
- Codespace downloads gist and unpacks files
- No need for artifact uploads or external storage

## Delimiter-Based File Packing

### Upload Format

**File**: `src/erk/cli/commands/exec/scripts/upload_learn_materials.py:41-60`

Each file is wrapped with delimiter lines and a `FILE:` header, then joined with blank line separators:

```python
# Key pattern (see source for full loop):
combined_parts.append(f"{'=' * 60}")        # Opening delimiter
combined_parts.append(f"FILE: {file_path.name}")  # Filename header
combined_parts.append(f"{'=' * 60}")        # Closing delimiter
```

**Example packed content**:

```
============================================================
FILE: planning-session-6491.xml
============================================================
<session>...</session>

============================================================
FILE: pr-comments.json
============================================================
[{"id": 123, "body": "Looks good!"}]

============================================================
FILE: metadata.json
============================================================
{"issue_number": 6491, "timestamp": "2024-..."}

```

### Download/Unpack Format

**File**: `src/erk/cli/commands/exec/scripts/download_learn_materials.py:174-207`

The parser uses a boolean `in_header` state toggle to walk through delimiters, extract filenames, and accumulate content:

```python
# Key parsing logic (see source for full implementation):
if line.strip() == "=" * 60:
    in_header = not in_header  # Toggle header state on delimiter
if in_header and line.startswith("FILE: "):
    current_filename = line[6:].strip()
```

## Delimiter Pattern Details

| Element               | Value              | Purpose                                                         |
| --------------------- | ------------------ | --------------------------------------------------------------- |
| **Opening delimiter** | `"=" * 60`         | Marks start of file header block                                |
| **Filename header**   | `FILE: {filename}` | Specifies output filename (basename only)                       |
| **Closing delimiter** | `"=" * 60`         | Marks end of file header block                                  |
| **Content**           | Raw file content   | Everything between closing delimiter and next opening delimiter |
| **Separator**         | Empty line         | Blank line after content (before next file's opening delimiter) |

### State Machine

The unpacker uses a state machine with two states:

1. **`in_header = False`** — Reading file content
2. **`in_header = True`** — Reading header block (between delimiters)

**Transitions**:

- `in_header = not in_header` on each delimiter line
- Parse `FILE: {name}` only when `in_header == True`
- Accumulate content lines only when `in_header == False`

## Round-Trip Guarantees

The format guarantees round-trip consistency:

**Upload**:

```python
files = [Path("session.xml"), Path("comments.json")]
packed_content = pack_files(files)
gist_url = upload_to_gist(packed_content)
```

**Download**:

```python
packed_content = download_from_gist(gist_url)
unpacked_files = unpack_files(packed_content)
# unpacked_files == original files (content preserved)
```

**Invariant**: If file content doesn't contain lines matching `"=" * 60`, unpacking is guaranteed to restore original content exactly.

**Edge case**: If file content contains a line of 60 equals signs, it will confuse the parser. Currently unhandled (no escaping mechanism).

## Raw Content URL Resolution

Gist raw content is fetched by `_download_gist_raw_content()` in `download_learn_materials.py:73-110`, which tries candidate URLs in order until one succeeds.

**Why multiple URLs**: GitHub gist raw URLs vary by context — `gist.githubusercontent.com/raw/{id}` works for public gists without knowing the owner, while `gist.github.com/{id}/raw` provides a fallback for different URL formats.

## Gist Metadata

Each gist uploaded for learn materials includes:

| File                               | Purpose                                    |
| ---------------------------------- | ------------------------------------------ |
| `learn-materials-plan-{issue}.txt` | Main packed file containing all materials  |
| Description                        | "Learn materials for plan #{issue_number}" |
| Public                             | No (secret gist for privacy)               |

**Source**: `upload_learn_materials.py:105-110`

## Related Documentation

- [Async Learn Local Preprocessing](../planning/async-learn-local-preprocessing.md) — How materials are generated and uploaded
- [Learn Workflow](../planning/learn-workflow.md) — Complete async learn flow
