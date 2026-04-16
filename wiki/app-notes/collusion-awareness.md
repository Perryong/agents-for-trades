---
title: Collusion Awareness — Regulatory Considerations
type: app-note
tags: [app-note, regulation, collusion, compliance, risk]
sources: [w34054.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## What to Change

Design our system with awareness of [[algorithmic-collusion]] risks to avoid regulatory exposure as AI trading regulations evolve. This does not require immediate code changes but establishes design principles and monitoring capabilities.

## Why (Source Citation)

Dou, Goldstein & Ji (2025) demonstrate that autonomous RL trading agents can develop collusive behavior without explicit communication:

- Q-learning agents sustain supra-competitive profits through price-trigger strategies and over-pruning bias, both without any coordination mechanism. [Source: w34054.pdf]
- Collusion degrades [[market-efficiency]]: lower liquidity, lower price informativeness, higher mispricing. [Source: w34054.pdf]
- AI collusion falls outside existing antitrust frameworks focused on detecting explicit communication. The SEC has already approved RL-based order types (Nasdaq), creating precedent. [Source: w34054.pdf]
- Collusion emerges robustly across a wide range of market parameters and RL hyperparameters. [Source: w34054.pdf]

While our system uses LLM agents (not RL traders), similar concerns apply: if multiple instances of our system or similar systems analyze the same data and reach similar conclusions, their correlated actions could constitute implicit coordination.

## Expected Impact

- **Regulatory preparedness**: Position ourselves ahead of likely regulation of AI trading systems
- **Audit trail**: Enable post-hoc analysis of whether our system's actions contributed to coordinated market behavior
- **Differentiation**: Demonstrate responsible AI trading practices to potential institutional users

## Implementation Notes

### Design Principles
1. **Decision diversity**: Introduce controlled randomization or diversity mechanisms in the trader agent's final decisions to avoid lockstep behavior with similar systems
2. **Independent data sources**: Where possible, use unique or less-common data sources alongside standard ones (Bloomberg, FinnHub) to reduce signal correlation with other AI systems
3. **Transparent reasoning**: Maintain detailed logs of the decision pipeline (analyst reports, debate transcripts, risk deliberations) to demonstrate that decisions are based on independent analysis, not emergent coordination

### Monitoring Capabilities
1. **Trade pattern analysis**: Track whether the system consistently trades in the same direction on the same securities at the same time as overall market AI flow
2. **Aggressiveness metrics**: Monitor the system's trading aggressiveness relative to its information signal strength — collusive behavior would show systematically conservative trading on strong signals [Source: w34054.pdf]
3. **Price impact awareness**: Track whether the system's trades consistently move prices in patterns that benefit subsequent trades

### Regulatory Documentation
1. Document that our system makes independent decisions based on its own analysis pipeline
2. Maintain records showing the diversity of inputs (four different analyst types, adversarial debate) that prevent single-signal dependence
3. Note that our risk management team structure (aggressive/neutral/conservative debate) naturally produces varied recommendations

### What NOT to Do
- Do not attempt to detect or respond to other AI systems' trading patterns (this could constitute explicit coordination)
- Do not share trading signals or strategies with other AI trading systems
- Do not use other AI systems' known strategies as inputs to our own decisions

## Cross-References

- [[algorithmic-collusion]] — the underlying concept
- [[market-efficiency]] — what collusion degrades
- [[tradingagents-framework]] — our system's architecture
- [[learning-externality-mitigation]] — related multi-agent design concern
