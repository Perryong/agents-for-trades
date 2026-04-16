---
title: "(Deep) Learning to Trade: An Experimental Analysis of AI Trading and Market Outcomes"
type: source
tags: [deep-reinforcement-learning, learning-externality, market-efficiency, multi-agent, DDPG, equilibrium]
sources: [Sangiorgi_Deep__Learning_to_Trade.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Citation

Gufler, I., Sangiorgi, F., & Tarantino, E. (2025). (Deep) Learning to Trade: An Experimental Analysis of AI Trading and Market Outcomes. Working Paper, September 2025. Luiss University, Frankfurt School of Finance and Management, European Commission.

## Summary

This paper embeds deep reinforcement learning (DRL) agents into a calibrated financial market with endogenous prices and return predictability to study how AI traders learn and how their interactions affect market outcomes. The key finding is a **negative [[learning-externality]]**: each agent's exploratory trades inject noise into the price process, contaminating the learning signals available to other agents. While individual AI traders qualitatively match a rational benchmark, they systematically fall short when multiple agents interact, degrading [[market-efficiency]] and liquidity relative to theoretical optimum. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Key Findings

- **Qualitative alignment with rational benchmark**: Individual AI traders learn portfolio policies that respond correctly to the composite signal z, internalize price impact, and adjust for competition, consistent with theory. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Negative learning externality**: When multiple AI traders interact, each agent's exploratory trades add variance to prices, diluting the learning signals available to others. No agent can disentangle its own price impact from noise created by peers. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Quantitative performance degrades with scale**: As the number of AI traders or their collective wealth share grows, systematic deviations from the rational benchmark emerge. Agents scale down positions too little when large and scale up too aggressively as competition intensifies. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Persistent market inefficiency**: Return predictability remains elevated and prices react more sharply to transitory supply shocks than in the rational benchmark, meaning AI traders leave exploitable patterns in the market. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Partial-equilibrium backtests overstate AI performance**: Testing on fixed historical data (where the agent's trades do not affect prices) overstates both the effectiveness of AI strategies and their positive market impact. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Distinct from collusion**: The experimental design prevents tacit collusion by restricting state space to exogenous variables. The degradation is purely informational, not strategic. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **DDPG agents used for continuous state/action spaces**: Unlike most prior work using tabular Q-learning, this paper employs deep deterministic policy gradient algorithms to handle the continuous nature of portfolio weights and market signals. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Methodology

- **Market model**: Demand-based asset pricing framework adapted from Koijen and Yogo (2019) with a representative investor, J traders, and endogenous price formation via market clearing. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **DRL algorithm**: Deep Deterministic Policy Gradient (DDPG) with actor-critic neural networks. Continuous state space (prices, characteristics) and continuous action space (portfolio weights). [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Data calibration**: Ten U.S. equities spanning a broad range of characteristics. Representative investor demand estimated empirically. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Benchmark**: Rational expectations equilibrium where speculators have full knowledge of the data-generating process, providing an upper bound on what algorithms could achieve. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Controlled experiments**: Vary number of AI traders, wealth share, and trading parameters to isolate the learning externality from other effects. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Relevance to AI Trading System

This paper's findings are directly relevant to our multi-agent architecture. While our system uses LLM agents (not RL traders), the principle that multiple AI systems learning from the same market signals degrade each other's performance applies broadly. The caution about partial-equilibrium backtesting is critical for our backtesting methodology. See [[learning-externality-mitigation]] for actionable notes.

## Cross-References

- [[learning-externality]] — the key concept introduced by this paper
- [[market-efficiency]] — how AI trading affects it
- [[algorithmic-collusion]] — related but distinct phenomenon from Paper 6
- [[learning-externality-mitigation]] — app note on mitigating these effects
