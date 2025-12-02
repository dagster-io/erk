# Core Style Guide: Foundational Principles

_Version 1.0_

## Purpose

This guide establishes the foundational voice and principles that remain constant across all technical writing, regardless of audience or format. These are the non-negotiables that create consistency and authenticity across all content.

**Note**: This style guide captures Nick Schrock's writing voice and approach to technical communication.

## Universal Voice Principles

### Personal Authority

- Ground all insights in concrete experience
- Use "I've seen," "I've built," "In my experience" to establish credibility
- Never hide behind passive voice or anonymous authority
- Own your opinions explicitly: "I believe" not "One could argue"

### Intellectual Honesty

- Acknowledge tradeoffs explicitly: "There are no solutions, only tradeoffs"
- Admit uncertainty: "I could be wrong," "Time will tell"
- Recognize when analysis isn't enough: "You just have to try it and see"
- Be transparent about biases: "My view is colored by my time at..."

### Constructive Frustration

- Channel genuine pain points into teaching moments
- Use frustration as a entry point: "There is little more frustrating than..."
- Transform complaints into systematic analysis
- Show you've felt this pain yourself before prescribing solutions

### Memorable Concepts

- Coin terms that capture complex ideas: "Parameter Anxiety," "God Class," "Medium-Code"
- Use these terms consistently throughout the piece
- Let memorable phrases carry conceptual weight
- Create mental handles people can reference later

### Practical Theory

- Never let abstractions float free from reality
- Connect economic theory to engineering decisions
- Ground philosophical points in concrete examples
- Always answer "So what should I do about it?"

## Universal Structural Elements

### The Hook

Every piece needs an opening that:

- Establishes why the reader should care
- Grounds the discussion in concrete reality
- Introduces the tension or problem
- Signals the kind of journey you're taking them on

### The Thread

Maintain a clear narrative line:

- Each paragraph should clearly connect to the next
- Use transitional phrases that show logical progression
- Return to your main thread after digressions
- End where you began (circle back to opening themes)

### The Payoff

Always deliver value:

- At least one actionable insight
- A new way of thinking about the problem
- Specific tactics or strategies
- A memorable framework or mental model

## Language Guidelines

### Active Voice and Ownership

- "I discovered" not "It was discovered"
- "We failed" not "Mistakes were made"
- "You should consider" not "One should consider"

### Precision with Accessibility

- Define technical terms inline, not in footnotes
- Use analogies to build intuition before precision
- Layer complexity progressively
- Never condescend—assume intelligence, not knowledge

### Memorable Phrasing

- Create quotable sentences that stand alone
- Use paradoxes to provoke thought
- Employ parallel structure for emphasis
- Make abstract concepts visceral through physical analogies

## Quality Checklist

Every piece must:

- [ ] Open with a hook that establishes stakes
- [ ] Include at least one memorable concept or phrase
- [ ] Provide concrete examples at the appropriate scale
- [ ] Acknowledge tradeoffs and limitations
- [ ] Offer practical takeaways
- [ ] Maintain consistent terminology throughout
- [ ] Circle back to opening themes in conclusion

## What to Avoid

### Empty Calories

- Throat-clearing introductions
- Unnecessary hedging that weakens points
- Abstract principles without examples
- Conclusions that merely summarize

### False Authority

- "Best practices" without justification
- "Everyone knows" assumptions
- Appeals to undefined authority
- Absolutist statements without evidence

### Lost Humanity

- Purely technical description without context
- Solutions without acknowledging the struggle
- Prescriptions without empathy
- Theory without practice

## The Signature Move

Regardless of audience or format, every piece should:

1. **Establish credibility through experience** - Not credentials, but battle scars
2. **Introduce a memorable concept** - Give people a new term or framework
3. **Show the pain viscerally** - Make readers feel the problem
4. **Provide handles for action** - Clear next steps or mental models
5. **Acknowledge the messiness** - Real world is complex, admit it

## Voice Temperature Check

Ask yourself:

- Would I say this to a colleague at a whiteboard?
- Is this how I'd explain it if someone was frustrated?
- Am I being honest about the tradeoffs?
- Will someone remember this next week?
- Can they do something with this information?

If any answer is "no," revise.

---

## References

This style guide was constructed from analysis of the following sources:

### Internal Technical Documentation

Code smell articles from internal GitHub discussions:

- [What are Code Smells?](https://github.com/dagster-io/internal/discussions/9542)
- [Using repr in Programmatically Significant Ways](https://github.com/dagster-io/internal/discussions/9505)
- [Excessive Use of Default Values on Parameters](https://github.com/dagster-io/internal/discussions/9509)
- [Operations that Mislead About Their Performance Characteristics](https://github.com/dagster-io/internal/discussions/9541)
- [Errors Too Deep in the Call Stack or Too Far into the Program](https://github.com/dagster-io/internal/discussions/9602)
- [Callsites with Multiple Non-Obvious Positional Parameters](https://github.com/dagster-io/internal/discussions/9682)
- [Invalid Parameter Combinations](https://github.com/dagster-io/internal/discussions/9694)
- [Using Overly Specific Context Objects in Context-Agnostic Code Paths](https://github.com/dagster-io/internal/discussions/9753)
- [Parameter Anxiety](https://github.com/dagster-io/internal/discussions/9719)
- [A God Class](https://github.com/dagster-io/internal/discussions/9791)
- [Too Many Local Variables](https://github.com/dagster-io/internal/discussions/9986)
- [Assigning Context Managers to Variables](https://github.com/dagster-io/internal/discussions/14241)

### External Blog Articles

- [The Rise of Medium-Code](https://dagster.io/blog/the-rise-of-medium-code)
- [On Code Reviews](https://medium.com/@schrockn/on-code-reviews-b1c7c94d868c)
- [Decade of Data Engineering](https://dagster.io/blog/decade-of-data-engineering)
- [Decade of Data](https://dagster.io/blog/decade-of-data)
- [Rebundling the Data Platform](https://dagster.io/blog/rebundling-the-data-platform)

---

_This core guide provides the foundation. Select a specific guide based on your article type for additional structure and patterns._
