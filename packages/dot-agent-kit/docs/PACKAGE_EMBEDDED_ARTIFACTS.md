# Package-Embedded Artifacts: AI-Native Libraries

## What This Enables

Library authors can embed Claude Code artifacts (skills, agents, commands) directly in their Python packages. When users install or upgrade the package, these artifacts automatically appear in `.claude/` — no additional setup required.

```bash
pip install your-framework
# .claude/skills/your-framework/ now exists
# Claude immediately knows how to use the framework
```

**The user doesn't need to know dot-agent exists.** They install your library, and Claude gets smarter about it. That's the entire user experience.

## Why This Matters

**Documentation becomes active.** Your carefully-written guides don't sit in `/docs` hoping someone reads them. They become instructions Claude follows when users write code with your library.

**Your expertise scales.** You know the right way to use your library — the patterns that work, the anti-patterns that cause bugs. Embedded artifacts encode that knowledge so every user benefits, not just those who read every page of documentation.

**Reduced support burden.** When Claude knows "don't use `sync_all()` in an async context" or "always call `configure()` before `run()`", users hit fewer footguns. Fewer GitHub issues asking the same questions.

**Zero friction for users.** No commands to run. No configuration. No awareness of the underlying kit system. Package installation is the only action.

## Use Cases

- **Frameworks** (Django, FastAPI): Teach Claude your routing patterns, middleware conventions, testing approaches
- **ORMs** (SQLAlchemy, Tortoise): Explain query patterns, relationship handling, migration workflows
- **Testing libraries** (pytest plugins): Guide assertion styles, fixture patterns, debugging approaches
- **CLI tools**: Include agents that operate your tool and parse its output
- **Domain-specific libraries**: Encode the mental model required to use your API effectively

## What You Can Embed

- **Skills**: Persistent knowledge Claude loads when working with your library
- **Agents**: Specialized sub-agents for complex workflows
- **Commands**: Slash commands for common operations (`/your-lib:init`, `/your-lib:migrate`)
- **Documentation**: Reference material skills can load on demand

## The Pitch

Your library already has great documentation. Package-embedded artifacts make that documentation _executable_ — Claude doesn't just know your API exists, it knows how to use it well. And your users get this for free, just by installing your package.
