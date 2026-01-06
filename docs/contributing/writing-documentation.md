# Writing Documentation

## How the documentation is organized

The documentation is organized into several categories:

### Tutorials (`tutorials/`)

Tutorials take the reader by the hand through a series of steps to create something.

The important thing in a tutorial is to help the reader achieve something useful,
preferably as early as possible, in order to give them confidence.

Explain the nature of the problem we're solving, so that the reader understands
what we're trying to achieve. Don't feel that you need to begin with explanations
of how things work - what matters is what the reader does, not what you explain.

**Title patterns**: "Your First X", "Getting Started with X"
**Test**: Can a beginner follow this and succeed?

### Topic guides (`topics/`)

Topic guides aim to explain a concept or subject at a fairly high level.

Link to reference material rather than repeat it. Use examples and don't be
reluctant to explain things that seem very basic to you - it might be the
explanation someone else needs.

Providing background context helps a newcomer connect the topic to things
that they already know.

**Title patterns**: Noun phrases ("Worktrees", "The Workflow")
**Test**: Does this help someone understand _why_, not _how_?

### Reference (`ref/`)

Reference guides contain technical references for APIs and configuration.
They describe the functioning of erk's internal machinery and instruct in its use.

Keep reference material tightly focused on the subject. Assume that the reader
already understands the basic concepts involved but needs to know or be reminded
of how erk does it.

Reference guides aren't the place for general explanation. If you find yourself
explaining basic concepts, you may want to move that material to a topic guide.

**Title patterns**: "X Reference", noun phrases matching CLI structure
**Test**: Is this pure description without instruction or explanation?

### How-to guides (`howto/`)

How-to guides are recipes that take the reader through steps in key subjects.

What matters most in a how-to guide is what a user wants to achieve. A how-to
should always be result-oriented rather than focused on internal details.

These guides are more advanced than tutorials and assume some knowledge about
how erk works. Assume that the reader has followed the tutorials and don't
hesitate to refer the reader back to the appropriate tutorial rather than
repeat the same material.

**Title patterns**: MUST work as "How to [title]"
**Test**: Does this answer a specific question an experienced user would ask?

## Framework Reference

Erk follows the [Divio Documentation System](https://docs.divio.com/documentation-system/).

Notable adopters: Django, NumPy, Cloudflare Workers.
