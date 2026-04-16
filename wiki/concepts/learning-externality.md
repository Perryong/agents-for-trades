---
title: Learning Externality
type: concept
tags: [multi-agent, reinforcement-learning, market-efficiency, DRL, noise, externality]
sources: [Sangiorgi_Deep__Learning_to_Trade.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Definition

A learning externality is a negative externality that arises when multiple AI trading agents learn simultaneously in a shared market. Each agent's exploratory trades inject order flow that is orthogonal to public information, adding variance to prices and diluting the learning signals available to all other agents. No agent can disentangle its own price impact from the noise created by peers, resulting in a friction that reduces individual performance and dampens the market-level benefits of algorithmic learning. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## How It Works

In a market with endogenous prices:

1. **Exploration injects noise**: Each DRL agent must explore (try different portfolio weights) to learn. These exploratory trades create order flow unrelated to fundamentals. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

2. **Prices absorb exploration noise**: Because prices are determined endogenously through market clearing, exploratory trades move prices, contaminating the price signal that all agents learn from. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

3. **Agents cannot filter peer noise**: Since no agent observes the identity, strategy, or actions of its peers, it cannot distinguish its own price impact from the systematic co-movement between peers' demand and fundamentals. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

4. **Learning quality degrades**: The contaminated price signals lead to suboptimal learned policies. Agents scale down positions too little when their size grows and scale up too aggressively as competition intensifies. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Empirical Evidence

Gufler, Sangiorgi & Tarantino (2025) demonstrate using DDPG agents in a calibrated market:

- Individual AI traders qualitatively match the rational expectations benchmark (correct policy direction). [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- As number of traders or collective wealth share increases, systematic quantitative deviations emerge. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Return predictability remains elevated (market is less efficient than benchmark). [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Prices react more sharply to transitory supply shocks (lower liquidity). [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Partial-equilibrium backtests (on fixed historical data) systematically overstate AI performance. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Distinction from [[algorithmic-collusion]]

The learning externality is **purely informational**, not strategic:
- **Collusion** (Dou et al., 2025): Agents develop coordinated behavior that benefits them collectively at the expense of market quality. [Source: w34054.pdf]
- **Learning externality** (Gufler et al., 2025): Agents degrade each other's learning without any strategic benefit to themselves. The experimental design explicitly prevents collusion by restricting state variables to exogenous factors. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

Both harm [[market-efficiency]], but through fundamentally different channels.

## Implications for AI Trading Systems

1. **Backtesting is insufficient**: Systems tested on historical data will appear more profitable and effective than they are in live markets where their trades affect prices. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
2. **Scaling is non-trivial**: Adding more AI agents or increasing capital does not linearly improve outcomes; it can degrade collective performance. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
3. **Market quality risk**: Widespread adoption of similar AI trading strategies may reduce rather than improve market efficiency and liquidity. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Relevance to Our System

Our [[tradingagents-framework]] is a multi-agent system where agents learn from shared market data. While our agents use LLMs rather than RL, the principle applies: if our system and similar systems all analyze the same news, filings, and price data, their correlated actions could inject systematic noise. See [[learning-externality-mitigation]] for design considerations.

## Cross-References

- [[algorithmic-collusion]] — related strategic phenomenon
- [[market-efficiency]] — affected by learning externalities
- [[learning-externality-mitigation]] — app note on mitigating these effects
- [[multi-agent-llm-trading]] — the paradigm affected by this finding
