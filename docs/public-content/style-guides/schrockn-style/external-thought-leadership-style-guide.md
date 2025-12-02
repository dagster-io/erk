# Style Guide: External Technical Thought Leadership

_For industry analysis, paradigm pieces, trend identification_

## Purpose

This guide covers writing for external technical audiences—the broader engineering community, potential customers, and industry peers. These pieces establish thought leadership, challenge conventional wisdom, and introduce new frameworks for thinking about technical problems.

## Voice Calibration

### Historical Authority

- Establish credibility through journey: "I was writing MapReduce jobs before Spark existed"
- Use temporal perspective: "Ten years ago, this would have been unthinkable"
- Reference industry evolution: "I've watched this pattern emerge at three companies"
- Position yourself as witness and participant: "From my perch at..."

### Confident Contrarian

- Challenge respectfully: "The conventional wisdom is wrong, but understandably so"
- Make bold claims with evidence: "Software-defined everything has gone too far"
- Acknowledge your minority position: "This might be controversial, but..."
- Own your predictions: "I believe we're about to see..."

### Accessible Expertise

- Build from first principles for newcomers
- Define industry terms naturally in flow
- Use universal metaphors before technical ones
- Never assume insider knowledge

## Document Structure

### 1. The Provocative Opening

Start with a claim that makes people think:

```
"Every configuration file is a cry for help."

"The cloud revolution we thought we were part of?
We might have gotten it backwards."

"Software-defined everything has gone too far."
```

### 2. The Personal Authority Bridge

Establish why you can make this claim:

```
"Let me explain. I've spent the last decade building
developer tools, first at Facebook where I watched..."
```

### 3. The Historical Arc

Show how we got here:

- Start with computing history (mainframes, UNIX)
- Trace evolution of current practices
- Identify the inflection point where things changed
- Show why the current approach made sense... then

### 4. The Tension Point

Identify what's breaking:

```
"This worked when deployments were quarterly. But now
we deploy hourly, and the assumptions no longer hold..."
```

### 5. The New Framework

Introduce your concept memorably:

```
"I call this 'Medium-Code'—the space between
clicking buttons and writing everything from scratch..."
```

### 6. The Evidence Mountain

Build your case from multiple angles:

- Industry examples (named companies)
- Technical demonstrations
- Economic arguments
- Historical parallels

### 7. The Implications

What this means going forward:

- For practitioners
- For tool builders
- For the industry
- For the next 5 years

## Language Patterns

### The Accessibility Ladder

Build concepts in layers:

1. **Universal metaphor**: "Like lawyers reviewing contracts..."
2. **Industry example**: "When Airbnb adopted Airflow..."
3. **Technical detail**: "The DAG scheduler has to..."
4. **Theoretical framework**: "This is classic bundling theory..."

### Quotable Constructions

Create sentences designed to be pulled out:

- Paradoxes: "The easier you make X, the more people will do X, but the less they'll understand it"
- Definitions: "Medium-Code (n): The practice of..."
- Predictions: "In five years, every data team will..."
- Challenges: "What if everything we believe about X is wrong?"

### The Teaching Voice

Guide readers through complexity:

- "Let me explain by starting with history..."
- "Bear with me through this technical detail—it matters because..."
- "If you've made it this far, you understand why..."
- "This might seem abstract, so let's make it concrete..."

## Content Templates

### Paradigm Shift Article

```markdown
# The Rise of [New Paradigm]

[Provocative opening claim]

## The Current Orthodoxy

[What everyone believes and why]

## Where It Breaks Down

[Specific evidence of failure]

## A Different Way of Thinking

[Introduce your framework]

## Evidence from the Field

- [Company A] discovered...
- [Company B] had to...
- [Industry trend] shows...

## What This Means for You

[Practical implications]

## Where We Go from Here

[Future projection]
```

### Industry Analysis Piece

```markdown
# [Surprising Observation about Industry]

[Personal hook establishing authority]

## What Changed

[The shift that nobody's talking about]

## The Data

[Charts, metrics, evidence]

## Why This Matters

[Connect to broader themes]

## The Path Forward

[Actionable insights]
```

## External-Specific Elements

### Name Names (Respectfully)

- "Databricks pioneered this approach with..."
- "The team at Airbnb discovered..."
- "Netflix's solution was elegant but..."
- Always punch up, never down

### Use Universal Examples

- Ford's assembly line for standardization
- Lawyers and contracts for configuration complexity
- Construction industry for modularity
- Publishing industry for bundling/unbundling

### Address Multiple Constituencies

Within the same piece, speak to:

- Individual practitioners ("You can start by...")
- Team leads ("Your team should consider...")
- Industry leaders ("The market is moving toward...")
- Vendors ("Tool builders need to...")

### Data-Driven Storytelling

- Include original data analysis where possible
- Create compelling visualizations
- Be transparent about methodology
- Acknowledge biases and limitations

## Quality Checklist

- [ ] Opens with a memorable/controversial claim
- [ ] Establishes personal authority early
- [ ] Builds concepts from first principles
- [ ] Challenges conventional wisdom respectfully
- [ ] Provides evidence from multiple sources
- [ ] Includes universal metaphors for accessibility
- [ ] Offers practical takeaways for different audiences
- [ ] Makes testable predictions about the future
- [ ] Acknowledges uncertainty and biases

## Examples of Strong Patterns

### The Historical Rhyme

"We're witnessing the UNIX philosophy play out again, but this time in the cloud. Small, focused services that do one thing well..."

### The Economic Frame

"This is classic bundling theory. When transaction costs are high, bundling wins. When they drop, unbundling follows. In developer tools..."

### The Contrarian Take

"Everyone's racing to make development easier. But what if that's exactly the wrong direction? Let me explain..."

### The Industry Prediction

"I believe we're about to see a fundamental shift in how companies build internal tools. The signs are already there if you know where to look..."

## What to Avoid

- Inside baseball without context
- Criticism without acknowledging tradeoffs
- Technical details without payoff
- Predictions without evidence
- Jargon without definition
- Problems without solutions

## The Thought Leadership Formula

Every piece should:

1. **Challenge** something widely believed
2. **Explain** why the belief exists
3. **Show** where it breaks down
4. **Introduce** a new framework
5. **Demonstrate** with evidence
6. **Project** implications
7. **Provide** practical steps

---

_Next: Select Practical Engineering Guides for how-to content_
