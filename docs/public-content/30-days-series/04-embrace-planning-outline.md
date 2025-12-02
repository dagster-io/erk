# Article Outline: Day Four - Embrace Planning

## Opening Hook

"Mainstreaming planning might be the true innovation of Claude Code. It's what separates AI-generated slop from production-ready code. And almost no one talks about it."

## The Vibe Coding Myth

- "The frustrating thing about conversations around agentic engineering is this notion that you can just chat informally with an AI and it'll divine what to build."
- "Garbage in, garbage out applies here too."
- Example: Show vague request that leads to Claude wandering through files, producing inconsistent code
- Contrast with: Same request after planning that executes cleanly in one pass

## Planning is Scatter/Gather for Code

- "Remember Day Three where we talked about Claude as investigator? Planning uses the exact same pattern."
- "During planning, the AI explores tons of code, reads documentation, understands patterns - the scatter phase"
- "Then it distills all that into a compact plan - the gather phase"
- "It's another read-only process where LLMs excel. Investigation for building, not just understanding."
- The plan becomes pre-computed context for execution

## The Shift+Tab Habit

- "In Claude, switching to plan mode is just Shift+Tab. That's it."
- "I rarely ask Claude to do work without planning first. You just get much, much better results."
- "It's become muscle memory: start typing request → Shift+Tab → refine in plan mode → execute"
- Show concrete before/after: quality difference between planned vs unplanned work

## What Planning Really Is

- "Extended iteration on a prompt until there's enough precision for complex execution"
- "Extracting tokens from your head and refining them until an agent can act"
- Show the progression:
  1. Vague thought: "Add authentication"
  2. Shift+Tab to plan mode
  3. Rough bullets: "JWT tokens, login endpoint, middleware"
  4. Structured plan: Specific files, patterns to follow, edge cases
  5. Executable specification: Complete blueprint Claude can follow

## The Unheralded Innovation

- "The Claude Code team quietly released a planning sub-agent - a huge advance that went mostly unnoticed"
- "Just weeks ago they updated it again. They're still iterating."
- "Sub-agents matter for managing context (more on this later in the series)"
- Why this matters: Planning agent can consume massive context, then compress it

## Real Example

- Show an actual planning session with Shift+Tab
- Walk through: initial request → plan mode → exploration → distillation
- Include the actual .PLAN.md file that resulted
- Show execution: How Claude followed the plan precisely
- Highlight what would've been impossible without planning

## Practical Takeaway

- "Try this tomorrow: Start every Claude session with Shift+Tab"
- "Let it explore widely, then distill. Watch the quality difference."
- "Within a week, it'll be muscle memory."
- Simple template to get started:
  - What files will be touched
  - What patterns to follow
  - What success looks like

## Conclusion/TL;DR

- Planning is how you get from "AI that writes slop" to "AI that ships features"
- It's just Shift+Tab, but it changes everything
- Start using it tomorrow - you'll see the difference immediately

---

## Key Points to Weave Throughout

1. **Planning as foundational skill** - It's what separates slop from production code
2. **Garbage in, garbage out** - Informal chat won't divine precise requirements
3. **Planning as prompt iteration** - Extended refinement until there's enough precision
4. **Token extraction** - Getting knowledge from your head into refineable form
5. **Scatter/gather pattern** - Connect to investigation from Day Three
6. **Shift+Tab simplicity** - Dead simple to use, massive impact
7. **Unheralded updates** - Claude team iterating quietly but significantly
