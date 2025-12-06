---
title: Raw Extraction Workflow
read_when:
  - "using raw session extraction"
  - "understanding /erk:create-raw-extraction-plan"
  - "automating documentation extraction"
  - "working with process-extraction.yml"
---

# Raw Extraction Workflow

End-to-end guide for the raw extraction workflow, which automates documentation extraction from Claude Code sessions through GitHub Actions.

## Overview

The raw extraction workflow enables fully automated documentation improvements:

1. **Local**: Run `/erk:create-raw-extraction-plan` to upload session data to a GitHub issue
2. **Remote**: GitHub Actions automatically processes the session and creates documentation PRs

This is ideal for:

- Batch processing of multiple sessions
- Asynchronous documentation extraction
- Leveraging CI resources for AI processing

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOCAL WORKSTATION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Claude Code Session                                                  │
│     └── Work on feature, fix bug, etc.                                   │
│                                                                          │
│  2. /erk:create-raw-extraction-plan                                      │
│     ├── Preprocess session log                                           │
│     ├── Create issue with erk-extraction label                           │
│     ├── Upload session XML as comments (chunked if large)                │
│     └── Title: "Raw Session Context: <description>"                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          GITHUB (Trigger)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Issue Created/Labeled                                                   │
│  - Has erk-extraction label                                              │
│  - Title starts with "Raw Session Context:"                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GITHUB ACTIONS WORKFLOW                             │
│                     (process-extraction.yml)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: Setup                                                          │
│  ├── Checkout repository                                                 │
│  ├── Install Claude Code, uv, erk tools                                  │
│  └── Configure git user                                                  │
│                                                                          │
│  PHASE 2: Extract Session Data                                           │
│  ├── dot-agent run erk extract-session-from-issue <issue_number>         │
│  ├── Parse session-content metadata blocks from comments                 │
│  └── Combine chunked XML into single file                                │
│                                                                          │
│  PHASE 3: Create Branch                                                  │
│  └── git checkout -b extraction-docs-<issue_number>                      │
│                                                                          │
│  PHASE 4: Analysis                                                       │
│  ├── Claude Code analyzes session XML                                    │
│  ├── Identifies documentation patterns (Category A & B)                  │
│  └── Creates .impl/plan.md with extraction plan                          │
│                                                                          │
│  PHASE 5: Implementation                                                 │
│  ├── /erk:plan-implement executes the plan                               │
│  └── Creates/updates documentation files                                 │
│                                                                          │
│  PHASE 6: Submission                                                     │
│  ├── /git:pr-push creates commit and PR                                  │
│  ├── Mark PR ready for review                                            │
│  └── Post completion comment to issue                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           PULL REQUEST                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PR: "Documentation extraction from issue #<N>"                          │
│  - New/updated documentation files                                       │
│  - Labeled for review                                                    │
│  - Links back to original issue                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Local Command: `/erk:create-raw-extraction-plan`

### What It Does

1. **Preprocesses the current session** - Converts JSONL log to compressed XML
2. **Creates GitHub issue** - With `erk-extraction` label and special title prefix
3. **Uploads session data** - As chunked metadata blocks in issue comments
4. **Outputs success message** - With issue URL and next steps

### Usage

```bash
/erk:create-raw-extraction-plan
```

Run this at the end of any session where you want to extract documentation patterns.

### Issue Structure

The command creates an issue with:

**Title format:**

```
Raw Session Context: <brief session description>
```

**Labels:**

- `erk-extraction` - Triggers the workflow

**Body:**

- Brief description of the session
- Metadata about the extraction

**Comments:**

- Session XML wrapped in `session-content` metadata blocks
- Chunked if content exceeds GitHub's 64KB comment limit

## Automatic Processing Trigger

The `process-extraction.yml` workflow triggers when:

```yaml
on:
  issues:
    types: [opened, labeled]

jobs:
  process-extraction:
    if: |
      contains(github.event.issue.labels.*.name, 'erk-extraction') &&
      startsWith(github.event.issue.title, 'Raw Session Context:')
```

Both conditions must be met:

1. Issue has `erk-extraction` label
2. Title starts with `Raw Session Context:`

## Session XML Storage

### Metadata Block Format

Session content is stored using the `session-content` metadata block:

````markdown
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data (1/3): feature-implementation</strong></summary>

```xml
<session session_id="abc123">
  ...
</session>
```
````

</details>
<!-- /erk:metadata-block:session-content -->
```

### Chunking Mechanism

Large sessions are automatically chunked:

- **Limit**: 64KB per comment (GitHub's maximum)
- **Safety buffer**: 1KB reserved for metadata overhead
- **Line-aware splitting**: Chunks never split mid-line

Chunk numbering appears in the summary:

- `Session Data (1/3)` - First of three chunks
- `Session Data (2/3)` - Second chunk
- `Session Data (3/3)` - Final chunk

### Extraction Hints

Optional hints can be included to guide the analysis:

```markdown
**Extraction Hints:**

- Error handling patterns
- Test fixture setup
- CLI output formatting
```

## Workflow Session Data Extraction

The workflow extracts session data using:

```bash
dot-agent run erk extract-session-from-issue <issue_number>
```

This command:

1. Fetches all comments from the issue
2. Parses `session-content` metadata blocks
3. Combines chunked content in order
4. Writes combined XML to scratch storage
5. Returns JSON with session file path and metadata

## Extraction Categories

The analysis phase identifies documentation in two categories:

### Category A: Learning Gaps

Documentation that would have made the session faster:

- Missing architectural explanations
- Undocumented patterns or conventions
- API quirks not covered in existing docs

### Category B: Teaching Gaps

Documentation for what was built:

- New features or commands
- Patterns discovered during implementation
- Reusable solutions worth documenting

## Raw vs Regular Extraction

### Raw Extraction (`/erk:create-raw-extraction-plan`)

**Use when:**

- You want fully automated processing
- The session is complete and ready for analysis
- You prefer asynchronous documentation extraction
- You want to batch multiple sessions

**How it works:**

- Uploads session data to GitHub
- Processing happens in GitHub Actions
- No local AI analysis required

### Regular Extraction (`/erk:create-extraction-plan`)

**Use when:**

- You want immediate local analysis
- You need to review/edit the plan before processing
- Network connectivity is limited
- You want more control over the extraction

**How it works:**

- AI analyzes session locally
- Creates plan file immediately
- You review and implement locally

## Workflow Status Comments

The workflow posts status updates as issue comments:

### Started

```
⚙️ **Documentation extraction started**

[Metadata block with timestamps]

---

Extracting session data from issue comments...

[View workflow run](...)
```

### Complete

```
✅ **Documentation extraction complete**

**PR:** <pr_url>

[Metadata block with timestamps]

---

The extraction has created documentation improvements. Please review the PR.
```

### Failed

```
❌ **Documentation extraction failed**

**Error:** <error message>

No session content was found in the issue comments...

[View workflow run](...)
```

## Debugging Extraction Issues

### Session Content Not Found

If extraction fails with "No session content found":

1. Check issue comments for `session-content` metadata blocks
2. Verify blocks have correct HTML comment markers
3. Ensure XML code fence is present within the block
4. Check for chunk ordering issues if content was chunked

### Workflow Not Triggering

If the workflow doesn't start:

1. Verify issue has `erk-extraction` label
2. Check title starts exactly with `Raw Session Context:`
3. Ensure workflow file exists and is on default branch
4. Check Actions tab for any workflow errors

### Analysis Phase Fails

If Claude Code analysis fails:

1. Check ANTHROPIC_API_KEY secret is set
2. Verify session XML is valid and complete
3. Review workflow logs for specific error messages
4. Ensure session contains meaningful content to analyze

## Related

- [Session Content Blocks](../sessions/session-content-blocks.md) - Metadata block format details
- [Claude Code in GitHub Actions](../reference/claude-code-github-actions.md) - CI/CD patterns
- [Planning Workflow](./workflow.md) - Understanding `.impl/` folders
