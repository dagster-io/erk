# Thirty Days of Agentic Engineering

I'm going to do an agentic engineering series that will serve as a practical guide for mastering Agentic Engineering. I'm testing the messaging internally before talking about it externally. This is the first piece.

I've been building in my spare time––and in gaps between meetings––CLI tools for agentic programming called `workstack` and `dot-agent`. They are useful tools for agentic engineering and my goal is to make their [codebase](https://github.com/dagster-io/workstack) a showcase and laboratory for these techniques. I've also started to use these in the Compass codebase and want to bring them to OSS, Internal, and other repositories as well.

_Note: This guide will be exclusively focused on Claude Code because that's what I use, but it applies to any agentic programming tool like Cursor or Codex._

## What I Mean by Context Engineering

When I say context engineering, I'm talking about deliberately managing what information the model has access to and when. You have to get the right context to the model at the right time. The model's output is completely bounded by what you put in—this includes your prompts, the code you show it, the structure of your project, everything.

It can't know about your internal abstractions or ontology; it can't follow your team's naming conventions if they're not in context; it can't debug an issue if the relevant code is in a file it can't see.

This seems obvious when you say it out loud, but in practice, most of us treat these tools like they should magically understand our codebase. They don't. They only know what we show them.

Additionally, beyond their world model they are stateless, which is counterintuitive given the frequent framing that AIs "learn". They actually don't learn at all. They are just fed better and more accurate context over time, which they have to evaluate, from scratch, with every request.

Agentic Engineering can be thought of as a subspecialty of context engineering focused purely on generating code.

## The Incremental Path

You can start getting value immediately and build up over time. Here's the progression I recommend:

### Read-only use cases

Start with the lowest-risk applications. AI tools excel at analyzing commit history to understand why code exists.

My first "a-ha" moment was with a simple prompt where Claude investigated what I thought was a problematic bit of code, found it in the history four years ago, and understood that it was no longer relevant because of an unsupported Python version, and suggested its deletion. It was correct. It was incredible.

Interpreting log messages or build failures is also a great initial use case. Just copy and paste a test failure or a Buildkite log and ask it to analyze and diagnose the error. It is remarkably good at that.

Or just ask it questions about unfamiliar code. It's amazing for gathering context and getting you up to speed about an unfamiliar system.

These use cases frequently deliver high value and are riskless. It's a great starting place.

### Standalone tools and CLIs

Many people say to start with test case generation. I explicitly recommend _not_ doing that, although lots of people do. If a unit of code is not set up for testability there's very little a bot (or a human) can do.

All too often, in an effort to do _something_ the agent will generate huge, brittle test cases with excessive mocking that don't test much. Given the constraint of _not_ touching production code, this is the best it can do (and does it better than you can), but it destroys trust in the ability for it to produce quality code.

Instead, build simple scripts and CLIs. These are additive tools that enhance your local development workflow or automate a manual process without touching production systems. Since they're self-contained (usually just one or two files), you limit the blast radius if something goes wrong. They are generally additive and therefore can be deleted without consequence.

### Bugs, features, and tests in existing codebases

This is where things get real. The stakes are higher—you need to learn how to guide the AI to write code that fits naturally into the existing codebase, following its patterns and conventions rather than introducing foreign styles that don't belong.

### After that, move up the complexity chain and build for others

I find that once you can confidently add features or fix bugs in a real production app, you are compelled to move up the complexity curve and build increasingly involved things with AI. You've gotten it to produce quality code and seen how you can get it to work more autonomously.

You'll also have enough confidence to set up infrastructure and norms for other people trying to ascend the learning curve of Agentic Engineering.

## You Have to Become an Expert

As you go up this escalating ladder of complexity and ambition, you have to become an expert in how these tools work. There is simply no way to abstract it away. These are complex machines and you have to become a power user.

Think of it more like flying an airplane. In the hands of a highly skilled pilot, an airplane is an extraordinarily powerful tool, allowing you to travel orders of magnitude more distance than you would otherwise. However, a bad pilot might crash the plane and die.

It's actually a fairly reasonable analogy for agentic programming. It can be extremely powerful, or you can end up committing huge amounts of bugs and bad code that could profoundly destabilize a system with AI slop.

Expertise here means building up enough intuition to know what context to feed the agent and when, and then enough skill to be able to act on that intuition. You have to get the right context to the right model at the right time. That is the core skill, and if you do that, you can become an extremely effective agentic programmer.

## The Transformative Potential

If we fully embrace these tools, I think it could be transformative for our organization. Individual engineers will become much more productive, and engineers (as well as other stakeholders) will have much higher dynamic range. Backend engineers can build frontend features. Frontend engineers can implement backend logic. Designers can directly build UI components. Everyone's capability envelope expands dramatically.
