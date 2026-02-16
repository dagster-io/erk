---
title: Gist Materials Interchange Format
read_when:
  - working with learn materials upload/download, debugging gist-based file transfer, implementing new file packing formats
last_audited: "2026-02-07 00:00 PT"
audit_result: clean
---

# Gist Materials Interchange Format

## Why Gists as Data Carrier?

GitHub Actions `workflow_dispatch` inputs accept strings, not file attachments. To transfer multiple files (session XML, PR comments, metadata) from local machine to GitHub Actions codespace, we pack all files into a single gist and pass its URL.

**Decision rationale**: Alternative approaches considered and rejected:

| Approach              | Why Rejected                                                    |
| --------------------- | --------------------------------------------------------------- |
| Artifacts API         | Requires existing workflow run; chicken-and-egg for triggers    |
| Separate gists        | Multiple URLs exceed `workflow_dispatch` input length limits    |
| Base64 in input       | GitHub has undocumented input size caps (~1MB); sessions exceed |
| External storage (S3) | Adds dependency; gists are GitHub-native and authenticated      |

Gists provide authenticated, ephemeral storage with a single URL reference. They're cleaned up manually after use, not relied upon for persistence.

## Delimiter-Based Packing Format

### Why Delimiters Instead of ZIP/Tar?

The gist content must be **human-readable** in the GitHub gist UI for debugging. When a learn workflow fails, developers inspect the gist manually to verify uploaded content. Binary archives would require download-and-extract, breaking the fast feedback loop.

**Trade-off**: Delimiter collision (if file content contains `"=" * 60`) breaks unpacking. This is acceptable because:

1. Session XML never generates 60 consecutive equals signs
2. JSON files (PR comments, metadata) don't use equals delimiters
3. Adding escaping would complicate both packer and parser

If this becomes a problem, switch to multipart MIME format (RFC 2046) instead of inventing escaping rules.

### Delimiter Pattern

<!-- Source: src/erk/cli/commands/exec/scripts/upload_learn_materials.py, combine_learn_material_files() -->

Each file is wrapped with 60-character equals-sign delimiters and a `FILE:` header. See `combine_learn_material_files()` in `src/erk/cli/commands/exec/scripts/upload_learn_materials.py`.

**Format structure:**

```
============================================================
FILE: filename.txt
============================================================
<file content verbatim>

============================================================
FILE: next-file.json
============================================================
<next file content>

```

**Key invariants:**

- Opening delimiter marks start of header block
- `FILE:` line contains basename only (no directory path)
- Closing delimiter marks end of header block
- Content starts immediately after closing delimiter
- Blank line separates files (before next opening delimiter)

### State Machine Parser

<!-- Source: src/erk/cli/commands/exec/scripts/download_learn_materials.py, download_learn_materials() -->

The unpacker uses a boolean toggle state machine. See the main loop in `download_learn_materials()` within `src/erk/cli/commands/exec/scripts/download_learn_materials.py`.

**States:**

| State               | Active When               | Action on Delimiter Line    |
| ------------------- | ------------------------- | --------------------------- |
| `in_header = True`  | Inside delimiter pair     | Parse `FILE:` line          |
| `in_header = False` | Outside delimiter pair    | Accumulate content lines    |
| Transition          | Every delimiter line read | `in_header = not in_header` |

**Why toggle state**: Simpler than tracking "looking for opening" vs "looking for closing" vs "reading content". Each delimiter line flips the state, maintaining the invariant that header blocks are always bracketed by pairs.

## Raw Content URL Resolution

<!-- Source: src/erk/cli/commands/exec/scripts/download_learn_materials.py, _download_gist_raw_content() -->

GitHub gist raw URLs vary by gist visibility and authentication context. The downloader tries candidate URLs until one succeeds. See `_download_gist_raw_content()` in `src/erk/cli/commands/exec/scripts/download_learn_materials.py`.

**URL candidates (in order):**

1. `https://gist.githubusercontent.com/raw/{gist_id}` — Works for public gists without knowing owner
2. `https://gist.github.com/{gist_id}/raw` — Fallback for secret gists with authenticated context

**Why try-until-success**: GitHub's gist URL scheme is undocumented. Public vs secret gists, authenticated vs anonymous access, and user-specific vs cross-account visibility all affect which URL works. Rather than detect all cases upfront (brittle), we try known patterns and use the first success.

If both URLs fail, the last HTTP error is raised. This preserves the original error message (404, 403, etc.) for debugging.

## Round-Trip Guarantees and Edge Cases

**Guaranteed round-trip**: If no file contains a line of exactly 60 equals signs, unpacking restores original content byte-for-byte.

**Edge case (unhandled)**: If file content includes `"=" * 60` as a literal line, the parser interprets it as a delimiter. The file will be split incorrectly, and unpacking fails silently (produces partial files with wrong boundaries).

**Why not escape**: Adding escape sequences (e.g., `\=============`) requires:

1. Escape routine in packer
2. Unescape routine in unpacker
3. Handling of escape character itself (if `\` appears in content)
4. Testing round-trips for all escape combinations

This complexity is unjustified for the current use case. If delimiter collision becomes real (not hypothetical), switch to multipart MIME instead of inventing escaping.

## Gist Metadata Convention

<!-- Source: src/erk/cli/commands/exec/scripts/upload_learn_materials.py, upload_learn_materials() -->

See the `github.create_gist()` call in `upload_learn_materials()` within `src/erk/cli/commands/exec/scripts/upload_learn_materials.py`.

| Field       | Value                                 | Purpose                                    |
| ----------- | ------------------------------------- | ------------------------------------------ |
| Filename    | `learn-materials-plan-{issue}.txt`    | Human-recognizable pattern for debugging   |
| Description | `"Learn materials for plan #{issue}"` | Links gist to plan issue in gist list view |
| Public      | `False` (secret gist)                 | Prevents indexing; rely on URL obscurity   |

**Why secret gists**: Session XML may contain API tokens, file paths, or other context we don't want indexed by search engines. Secret gists aren't truly private (anyone with URL can access), but they're excluded from GitHub's public gist listings and search.

Gists are deleted manually after learn completes. There's no automatic cleanup; this is acceptable because learn runs infrequently and gists are small (<1MB typically).

## Related Documentation

- [Async Learn Local Preprocessing](../planning/async-learn-local-preprocessing.md) — How materials are generated and uploaded (Step 5 of 6-step orchestration)
- [Learn Workflow](../planning/learn-workflow.md) — Complete async learn flow and agent tier architecture
