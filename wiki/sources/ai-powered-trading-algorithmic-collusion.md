---
title: "AI-Powered Trading, Algorithmic Collusion, and Price Efficiency"
type: source
tags: [algorithmic-collusion, reinforcement-learning, market-efficiency, regulation, Q-learning, price-trigger]
sources: [w34054.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Citation

Dou, W. W., Goldstein, I., & Ji, Y. (2025). AI-Powered Trading, Algorithmic Collusion, and Price Efficiency. NBER Working Paper No. 34054. University of Pennsylvania (Wharton), Hong Kong University of Science and Technology (HKUST).

## Summary

This paper investigates whether autonomous RL-based trading agents can develop collusive behavior in financial markets without explicit communication or intent. Using a theoretical model extending Kyle (1985) with oligopolistic informed speculators, information-insensitive investors, and an inventory-aware market maker, the authors first establish theoretical benchmarks (non-collusive Nash equilibrium and perfect cartel). They then replace human speculators with Q-learning algorithms and demonstrate that [[algorithmic-collusion]] arises robustly across a wide range of market parameters through two distinct mechanisms. [Source: w34054.pdf]

## Key Findings

- **Two distinct collusion mechanisms identified**: (1) Price-trigger strategies ("artificial intelligence") where agents learn to trade conservatively and punish deviations when prices reveal aggressive trading, and (2) Over-pruning bias ("artificial stupidity") where RL's asymmetric Q-value updates systematically under-value aggressive strategies. [Source: w34054.pdf]
- **Price-trigger collusion** emerges in environments with low noise trading risk and significant information-insensitive investor presence, where lagged prices are highly informative. [Source: w34054.pdf]
- **Over-pruning collusion** arises when noise dominates, causing asymmetric Q-value updates: large losses from noise-aligned trades sharply lower Q-values for aggressive strategies, while gains are corrected through repeated exploitation. [Source: w34054.pdf]
- **Collusion degrades market quality**: Greater collusion leads to lower market liquidity, lower price informativeness, and higher mispricing, regardless of which mechanism drives it. [Source: w34054.pdf]
- **Robust across RL hyperparameters**: Collusive behavior and supra-competitive profits persist across a broad range of learning rates, exploration decay rates, and discount factors. [Source: w34054.pdf]
- **Regulatory gap**: AI collusion falls outside existing antitrust frameworks that focus on detecting explicit communication or shared intent. The Sherman Act applies but enforcement is unclear. [Source: w34054.pdf]
- **Parameter-dependent mechanism selection**: Fewer informed speculators, lower noise risk, and higher discount factors increase price-trigger collusion capacity; lower noise risk reduces over-pruning collusion. [Source: w34054.pdf]

## Methodology

- **Theoretical model**: Extended Kyle (1985) with multiple informed speculators trading repeatedly, information-insensitive investors providing downward-sloping demand, and an inventory-aware market maker. [Source: w34054.pdf]
- **Simulation**: Q-learning algorithms replace informed speculators. State vector includes lagged market price, lagged fundamental value, and current fundamental value. Standard exploration-exploitation with decaying exploration. [Source: w34054.pdf]
- **Benchmarks**: Non-collusive Nash equilibrium (competitive) and perfect cartel (joint profit maximization). Collusion measured by supra-competitive profits falling between these bounds. [Source: w34054.pdf]
- **Parametric sweep**: Extensive variation of market parameters (number of speculators, noise trading risk, information-insensitive investor presence, discount factor) and RL hyperparameters. [Source: w34054.pdf]

## Relevance to AI Trading System

While our system uses LLM agents rather than RL agents, the findings have important regulatory implications. If multiple instances of our system (or similar systems) operate in the same market, emergent coordination could draw regulatory scrutiny even without explicit intent. See [[collusion-awareness]] for actionable notes on how to design our system with these risks in mind. The over-pruning bias finding also informs [[market-efficiency]] discussions.

## Cross-References

- [[algorithmic-collusion]] — concept page on this phenomenon
- [[market-efficiency]] — how AI trading affects price efficiency
- [[collusion-awareness]] — app note on regulatory considerations
- [[learning-externality]] — related but distinct phenomenon from Paper 7
