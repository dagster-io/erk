# Agentic Programming Articles - Workflow

## Article Status Workflow

Articles in this collection follow a three-stage lifecycle:

### 💡 Idea Stage

- Article concept captured in `articles/ideas.md`
- No file created yet
- No status marker (default state)

### 📝 Draft Stage

- Article written and saved to appropriate directory
- File exists in repo (e.g., `docs/public-content/30-days-series/01-intro.md`)
- Not yet posted publicly
- Marked with 📝 in `articles/ideas.md`
- **Criteria:** Has local file, but NO GitHub discussion link

### ✅ Published Stage

- Article posted to internal GitHub discussions
- Has GitHub discussion link in `articles/ideas.md`
- Marked with ✅ in `articles/ideas.md`
- **Criteria:** Has GitHub discussion link

## Publishing Workflow

1. **Write** - Create article file in appropriate directory
2. **Update ideas.md** - Mark as 📝 Draft with file location
3. **Post** - Share to internal GitHub discussions at https://github.com/dagster-io/internal/discussions
4. **Update ideas.md** - Change to ✅ Published and add GitHub discussion link

## Status Tracking Format

```markdown
38. **Article Title** ✅ - Description
    - Location: `path/to/file.md`
    - Posted: https://github.com/dagster-io/internal/discussions/XXXXX
```

**Draft format:**

```markdown
38. **Article Title** 📝 - Description
    - Location: `path/to/file.md`
```

**Idea format:**

```markdown
38. **Article Title** - Description
```

## Important Notes

- Articles are ONLY considered complete when they have a GitHub discussion link
- Draft files without GitHub links remain in 📝 Draft status
- The GitHub discussion link is the source of truth for publication status
