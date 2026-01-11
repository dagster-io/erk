# Writing Documentation

This guide explains how to write and organize documentation for erk using the Divio Documentation System.

## The Divio Framework

`erk`'s documentation follows the [Divio Documentation System](https://documentation.divio.com/), which organizes content into four categories based on user intent:

| Category  | Purpose              | User Intent    | Directory    |
| --------- | -------------------- | -------------- | ------------ |
| Tutorials | Learning-oriented    | "Teach me"     | `tutorials/` |
| Topics    | Understanding        | "Explain this" | `topics/`    |
| How-to    | Goal-oriented        | "Help me do X" | `howto/`     |
| Reference | Information-oriented | "Look up Y"    | `ref/`       |

This system is used by Django, NumPy, Cloudflare Workers, and many other projects.

## Category Definitions

### Tutorials

**Purpose:** Learning-oriented lessons that guide beginners through a series of steps.

**Characteristics:**

- Step-by-step instructions
- Focus on learning, not accomplishing a task
- Explain what's happening and why
- Build toward a working result

**Title pattern:** Use descriptive names (no special prefix)

**Example:** "Your First Plan" guides users through creating and executing their first plan.

**Test question:** Does this teach a skill through hands-on practice?

### Topics

**Purpose:** Understanding-oriented explanations of concepts and ideas.

**Characteristics:**

- Explain "why" and "how things work"
- Provide context and background
- Connect concepts to each other
- Don't require following along

**Title pattern:** Noun phrases describing the concept

**Example:** "Worktrees" explains what git worktrees are and why erk uses them.

**Test question:** Does this help someone understand a concept?

### How-to Guides

**Purpose:** Goal-oriented instructions for accomplishing specific tasks.

**Characteristics:**

- Task-focused, not learning-focused
- Assume basic knowledge
- Get to the point quickly
- Cover one specific goal

**Title pattern:** Must work as "How to [title]"

| Title                   | How to...                      |
| ----------------------- | ------------------------------ |
| Use the Local Workflow  | How to use the local workflow  |
| Resolve Merge Conflicts | How to resolve merge conflicts |
| Work Without Plans      | How to work without plans      |

**Test question:** Does this help someone accomplish a specific goal?

### Reference

**Purpose:** Information-oriented technical specifications.

**Characteristics:**

- Complete and accurate
- Consistent structure
- No explanation or guidance
- Optimized for lookup, not reading

**Title pattern:** Use "X Reference" suffix

| Title                   | Content                        |
| ----------------------- | ------------------------------ |
| CLI Command Reference   | All CLI commands and options   |
| Configuration Reference | All configuration options      |
| File Location Reference | All file paths and directories |

**Test question:** Does this provide technical details for lookup?

## Choosing the Right Category

Use these questions to categorize new content:

1. **Is this teaching a beginner?** → Tutorial
2. **Does this explain concepts or theory?** → Topic
3. **Does this solve a specific problem?** → How-to
4. **Is this a technical specification?** → Reference

### Common Mistakes

| Content Type                   | Wrong Category | Right Category |
| ------------------------------ | -------------- | -------------- |
| "Introduction to worktrees"    | Tutorials      | Topics         |
| "Worktree CLI Reference"       | Topics         | Reference      |
| "Why we use worktrees"         | How-to         | Topics         |
| "Create a worktree for a plan" | Reference      | How-to         |

## File Structure

Each category directory contains:

- `index.md` - Section overview for navigation (MkDocs)
- `README.md` - Section overview for GitHub viewing
- Individual topic files

### File Naming

- Use lowercase with hyphens: `local-workflow.md`
- Keep names short but descriptive
- Avoid abbreviations unless widely known

## Cross-References

When linking to other documentation:

- Use relative paths: `../topics/worktrees.md`
- Link to related content in a "See Also" section
- Use the new title conventions when referring to documents

### Directory Mappings

| Old Directory      | New Directory |
| ------------------ | ------------- |
| `getting-started/` | `tutorials/`  |
| `concepts/`        | `topics/`     |
| `guides/`          | `howto/`      |
| `reference/`       | `ref/`        |
| `troubleshooting/` | `faq/`        |

## See Also

- [Divio Documentation System](https://documentation.divio.com/) - Full framework documentation
- [Django Documentation](https://docs.djangoproject.com/) - Example implementation
