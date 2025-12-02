# Day One: Always Run Claude in Verbose Mode

Claude has a verbose mode. It's not emphasized and it's off by default. In my opinion it should be the default mode. It's easy to enable and not _that_ verbose in practice.

```bash
claude --verbose
```

Turning verbose mode on exposes more of Claude's reasoning in realtime and always tells you the exact number of tokens in the context window. With just these two features along you learn about Claude much more quickly.

## Reasoning

Here's a real life example of verbose mode working well. I gave it a fairly rough prompt and an image while working on a toy app. Everything below "Thinking" is only visible in verbose mode. It gives valuable insight into what Claude understands.

```
"error loading todos" and the icon is messed up
∴ Thinking…
  The user is showing me a screenshot of the app running. Two issues:
  1. "Error loading todos" - the todos aren't loading
  2. The icon is messed up
  Let me debug this:
  1. The CLI path might be wrong in the cli-wrapper.js
  2. The icon might need to be a template image for menu bar
  Let me check the issues:
  - The CLI path is set to path.join(KNOWLEDGE_ROOT, '.venv', 'bin', 'knowledge')
  - KNOWLEDGE_ROOT is path.join(__dirname, '..', '..') which from electron-knowledge/lib/ would be the knowledge repo root
  - That should be correct
```

You can also halt Claude earlier in the process if it reasons about something incorrectly, rather than having to wait for it to produce incorrect output and reconstruct the exact thing it misunderstood.

## Token Count

It also adds a very useful label on the bottom right: exact token count.

```bash
40128 tokens
```

It is visible your entire sessions rather than when you are approaching your limits. It gives you valuable insight. You'll know how big the system prompt is (turns out ~25K tokens), how much room your CLAUDE.md occupies (you can see it go up when it loads) and what consumes tokens versus what does not generally as your agent works.

## TL;DR

Just turn it on. You'll build intuition about what Claude is doing more quickly. I have `alias claude='claude --verbose'` in my `.zshrc`. Highly recommended.
