# Day Three: Start with Claude as Investigator

The best way to build confidence with agentic programming is to start where the stakes are zero and the value is immediate: investigation.

LLMs are exceptionally good at consuming large amounts of scattered context and synthesizing it into compressed, actionable understanding. It turns out software engineering is full of tasks that fit exactly this pattern.

Use these tasks to get immediate value while building confidence in the tool's capabilities. With zero risk.

## Why Investigation Works

The pattern of going from scattered context to synthesized understanding is exactly what LLMs excel at. You can then extend it to do reasoning based on that analysis.

You see it work before trusting it with writing code or mutating state. You learn how to provide context effectively. You develop intuition for what it's good at.

## Examples

### Git archaeology

My first "a-ha moment" was asking Claude to investigate what I thought was problematic code. It searched through commit history, found the code was added four years ago for an unsupported Python version, and correctly suggested deletion of that code. It did that because it looked in our `setup.py` to see what versions of Python we support. Magical.

More recently, I used it to investigate our billing system's history—what bugs occurred, what changes were made, why decisions were made and so forth. I learned a massive amount in an extremely short time. It synthesized months of scattered commits, PRs, and issues into a coherent narrative.

### Log interpretation

Copy and paste CI failures, Buildkite logs, test output, or stack traces. Claude excels at pattern matching and diagnosis. It suggests bug fixes as well, if you ask it. Moving from synthesis to diagnosis is also a great way to get a sense of the reasoning power of models, especially when paired with verbose mode.

This is a natural point of automation as well. I've gone further and written automations that query Buildkite for failures and then have Claude automatically resolve the issue. Much of the time it can do this autonomously. However, analysis and diagnosis are a good place to start.

### Performance debugging

Another good use case is performance debugging. Analyzing performance is often an exercise in gathering massive amounts of context and distilling that context into a targeted fix. Another task that LLMs are well-suited to support.

For example, I use this to find and debug slow test cases. Slow tests are not just annoying: they are often symptoms of an "architectural smell" where the system is poorly structured or abstracted such that you cannot isolate specific parts of the system for testing.

Ask it to find the slowest test cases, and then ask it why they are slow. Ask it what we could do to speed it up. Prompt it to not just change infrastructure, but to change the structure of the production code to facilitate better testing. It works very well.

### Code understanding

Interrogating unfamiliar codebases: "Trace what happens when a user clicks this button." "What are the 10 most important files to understand this service?" You get architectural comprehension without reading everything linearly.

Each of these follows the same pattern: lots of scattered context gets compressed into actionable understanding. The Anthropic team reported that Claude dramatically reduces the time to onboard new team members, and it makes total sense.

## Conclusion

LLMs excel at synthesis: consuming scattered context and compressing it into understanding. Software engineering is full of these investigative tasks—git archaeology, log interpretation, performance debugging, code comprehension. Start here: immediate value, zero risk, builds confidence for more ambitious work later.
