---
title: Algorithmic Collusion
type: concept
tags: [collusion, reinforcement-learning, regulation, market-efficiency, Q-learning]
sources: [w34054.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Definition

Algorithmic collusion occurs when autonomous, self-interested AI trading algorithms independently learn to coordinate their trading in a way that secures supra-competitive profits, without explicit agreements, communication, or pre-programmed intent. The algorithms trade less aggressively on their private information than the competitive equilibrium would dictate, effectively behaving as a partial cartel. [Source: w34054.pdf]

## Two Mechanisms

Dou, Goldstein & Ji (2025) identify two fundamentally distinct algorithmic mechanisms:

### 1. Price-Trigger Strategies ("Artificial Intelligence")
When market prices are sufficiently informative, RL agents learn to trade conservatively because they recognize that aggressive trading would be detected via price movements, triggering "punishment" by other agents reverting to aggressive (competitive) strategies. This closely resembles the collusive Nash equilibrium sustained by price-trigger strategies in game theory (Green & Porter, 1984; Abreu, Pearce & Stacchetti, 1986). [Source: w34054.pdf]

**Conditions for emergence**:
- Low noise trading risk (prices are informative)
- Significant presence of information-insensitive investors
- Lagged prices serve as effective monitoring devices

**Behavioral pattern**: Mostly conservative trading with moderate price reactions, punctuated by occasional "punishment phases" of aggressive trading following large price movements. [Source: w34054.pdf]

### 2. Over-Pruning Bias ("Artificial Stupidity")
A learning bias inherent in RL's exploration-exploitation trade-off. When noise traders happen to trade in the same direction as the algorithm, aggressive strategies incur large losses, sharply lowering their Q-values. The algorithm prematurely prunes these strategies. Conversely, when noise traders trade opposite, the algorithm profits and frequently re-exploits those strategies, eventually correcting the Q-value. This asymmetry systematically biases the value system toward conservative (collusive) strategies. [Source: w34054.pdf]

**Conditions for emergence**:
- High noise trading risk (prices are noisy)
- Limited information-insensitive investor presence
- Arises across the entire parameter space where price-trigger collusion fails
- Independent of discount factor

[Source: w34054.pdf]

## Market Impact

Regardless of mechanism, greater collusion leads to:
- **Lower market liquidity**: Informed traders withhold trading activity
- **Lower price informativeness**: Prices reflect less fundamental information
- **Higher mispricing**: Larger deviations between prices and fundamental values

[Source: w34054.pdf]

## Regulatory Implications

AI collusion poses a unique regulatory challenge because it falls outside existing antitrust frameworks that require evidence of explicit communication or shared intent. The SEC recently approved Nasdaq's RL-based AI-driven order type, and leading hedge funds are increasingly adopting AI for trading. Current enforcement under the Sherman Act is unclear for collusion that emerges from independent learning without any coordination. [Source: w34054.pdf]

## Distinction from [[learning-externality]]

Algorithmic collusion involves strategic coordination (even if unintentional) that benefits the colluding agents at the expense of market quality. The [[learning-externality]] identified by Gufler, Sangiorgi & Tarantino (2025) is purely informational — agents degrade each other's learning through noise injection without any strategic benefit. Both harm [[market-efficiency]] but through different channels. [Source: w34054.pdf, Sangiorgi_Deep__Learning_to_Trade.pdf]

## Relevance to Our System

Our [[tradingagents-framework]] uses LLM agents rather than RL traders, so the specific Q-learning mechanisms do not directly apply. However, if multiple instances of our system (or similar LLM trading systems) operate in the same market with similar analytical frameworks, emergent behavioral correlation could raise similar concerns. See [[collusion-awareness]] for design considerations.

## Cross-References

- [[market-efficiency]] — how collusion affects price efficiency
- [[collusion-awareness]] — app note on regulatory design
- [[learning-externality]] — related but distinct degradation mechanism
