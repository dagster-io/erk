---
title: Canonical Authority Declarations
read_when:
  - writing documentation that could conflict with other sources
  - clarifying which doc is authoritative for a pattern
  - organizing documentation to prevent duplication
last_audited: "2026-02-05"
audit_result: clean
---

# Canonical Authority Declarations

Documentation in `docs/learned/` declares canonical authority to prevent ambiguity when multiple sources could document the same pattern. An explicit authority statement tells readers "this is the authoritative reference—don't look elsewhere."

## The Pattern

When a document is the definitive reference for a pattern, declare it explicitly:

```markdown
This is the canonical reference for [specific topic].
```

Place the declaration:

- **After the main explanation** (not in the frontmatter or introduction)
- **Before "Related Documentation" section**
- **As its own paragraph or sentence**

## When to Use Canonical Authority Declarations

Use this pattern when:

1. **Multiple sources could document the topic**
   - The pattern exists in code comments, AGENTS.md, and learned docs
   - Other team members might duplicate documentation elsewhere

2. **The pattern has complex nuances**
   - Session ID substitution differs in commands vs hooks
   - Gateway ABC implementation requires 5-place consistency

3. **The documentation consolidates scattered knowledge**
   - Previously spread across code comments and chat discussions
   - Gathered from multiple PRs and implementation sessions

**Skip the declaration** when:

- The topic is obviously unique (e.g., "TUI Command Palette Implementation")
- The document is a reference list (e.g., "Erk Exec Commands")
- The content is exploratory or observational, not definitive

## Examples from Existing Documentation

### Example 1: Session ID Substitution

From `docs/learned/commands/session-id-substitution.md:136`:

```markdown
This is the canonical reference for session ID access patterns.
```

**Why this works:**

- Session ID handling differs between commands and hooks
- AGENTS.md provides abbreviated version for quick reference
- This doc is the authoritative deep-dive with all edge cases

### Example 2: Gateway ABC Implementation

From `docs/learned/architecture/gateway-abc-implementation.md:38-59`:

```markdown
See the canonical implementation at `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py:38-59`.
```

**Why this works:**

- Points to canonical code implementation (not documentation)
- Multiple gateway implementations exist; this is the reference pattern
- Readers know which file to study for the correct approach

### Example 3: Discriminated Union Error Handling

From `docs/learned/architecture/discriminated-union-error-handling.md`:

```markdown
Examples in this document reference actual type definitions. See canonical sources:
```

**Why this works:**

- Documentation discusses patterns from multiple real implementations
- Explicitly lists canonical source files for each pattern
- Prevents confusion about "which file is the real example?"

## Relationship to Source Pointers

Canonical authority declarations complement [source-pointers.md](source-pointers.md):

| Pattern                             | Purpose                                     | Example                                             |
| ----------------------------------- | ------------------------------------------- | --------------------------------------------------- |
| **Canonical authority declaration** | Declares this doc is authoritative          | "This is the canonical reference for X"             |
| **Source pointer**                  | Points to authoritative code implementation | `See ClassName.method() in path/to/file.py:123-145` |

Use both together:

1. **Declare canonical authority** for the documentation
2. **Use source pointers** to reference the code implementation

This prevents documentation duplication AND code block staleness.

## Anti-Patterns

### Anti-Pattern 1: Declaring Authority Without Substance

**Wrong**:

```markdown
# Session ID Handling

This is the canonical reference for session IDs.

(document contains only 3 lines of explanation)
```

**Why wrong**: Claiming authority without comprehensive coverage misleads readers.

### Anti-Pattern 2: Multiple Canonical Declarations for Same Topic

**Wrong**:

- `docs/learned/commands/session-ids.md`: "This is the canonical reference for session ID patterns"
- `docs/learned/hooks/session-access.md`: "This is the canonical reference for session ID access"

**Why wrong**: Contradicts the purpose—now readers don't know which is authoritative.

**Fix**: Consolidate into one doc, or differentiate scope ("canonical for hooks" vs "canonical for commands").

### Anti-Pattern 3: Overusing Declarations

**Wrong**: Every document declares itself canonical, even for trivial topics.

**Why wrong**: Dilutes the signal. Reserve declarations for topics with genuine ambiguity or complexity.

## When Source Code is Canonical

Sometimes the code is the canonical reference, not documentation:

```markdown
See `ClassName.method()` in `path/to/file.py:123-145` for the canonical implementation.
```

Use this when:

- **The code is stable and well-structured**
- **Documentation would just duplicate the code comments**
- **The pattern is best understood by reading the implementation**

This inverts the authority: code is canonical, docs are supplementary.

## Related Documentation

- [source-pointers.md](source-pointers.md) - How to reference canonical code implementations
- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) - Why source pointers prevent documentation drift
