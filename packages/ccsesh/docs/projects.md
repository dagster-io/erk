# Projects Directory Structure

Claude Code stores all project and session data under `~/.claude/projects/`.

## Directory Layout

```
~/.claude/projects/
├── -Users-alice-code-myapp/              # Project folder (path-encoded)
│   ├── 1a2b3c4d-5e6f-7890-abcd-ef1234567890.jsonl    # Session file
│   ├── 2b3c4d5e-6f78-9012-bcde-f12345678901.jsonl    # Another session
│   └── 1a2b3c4d-5e6f-7890-abcd-ef1234567890/         # Session data folder
│       └── tool-results/
│           └── toolu_01ABC123.txt                     # Large tool output
├── -Users-alice-code-other-project/
│   └── ...
└── ...
```

## Path Encoding

Project folders use path encoding to create unique folder names:

| Original Path             | Encoded Folder Name       |
| ------------------------- | ------------------------- |
| `/Users/alice/code/myapp` | `-Users-alice-code-myapp` |
| `/home/bob/projects/api`  | `-home-bob-projects-api`  |

The encoding simply replaces `/` with `-`.

## Project Folder Contents

Each project folder contains:

### Session Files (`.jsonl`)

- Named with UUIDs: `{uuid}.jsonl`
- One file per session/conversation
- JSONL format (one JSON object per line)
- See [Sessions](sessions.md) for format details

### Session Data Folders (optional)

Some sessions have an associated folder named with the same UUID:

```
{uuid}/
├── session-memory/              # (deprecated)
│   └── summary.md
└── tool-results/
    └── toolu_01ABC123.txt       # Large tool output stored externally
```

**tool-results/**: When a tool produces output that exceeds the inline limit, Claude Code stores it in a separate file. The message references this file via a special marker.

**session-memory/**: An older mechanism for session state. Deprecated in favor of the summary line in the JSONL file.

## Finding Projects

To list all projects:

```bash
ls ~/.claude/projects/
```

To decode a project folder back to the original path:

```bash
# -Users-alice-code-myapp -> /Users/alice/code/myapp
echo "-Users-alice-code-myapp" | tr '-' '/'
```

Note: This simple decoding assumes no hyphens in the original path. Paths with hyphens are ambiguous.
