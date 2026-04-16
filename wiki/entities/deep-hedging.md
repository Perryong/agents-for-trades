---
title: Deep Hedging
type: entity
tags: [model, deep-learning, options-hedging, neural-network, risk-management]
sources: [ssrn-6339420.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Description

Deep Hedging is an RL-based approach to options hedging introduced by Buehler, Gonon, Teichmann & Wood (2019) in "Deep Hedging" (Quantitative Finance, 19(8), 1271-1291). It uses neural networks to learn hedging policies that can optimize under different risk measures, including Expected Shortfall. It was a pioneering work that advanced RL-based hedging beyond the discrete formulation of [[qlbs-model]] by enabling the inclusion of transaction costs and market frictions in the optimization. [Source: ssrn-6339420.pdf]

## How It Works

Deep Hedging trains a neural network to output hedging actions given the current market state. The network learns a policy that minimizes a chosen risk measure (typically Expected Shortfall or CVaR) of the hedging portfolio's terminal P&L, incorporating:
- Transaction costs (proportional or fixed)
- Market frictions
- Discrete rebalancing schedules

The approach is model-free in the sense that it does not require a specific parametric pricing model, instead learning directly from simulated or historical price paths.

## Distinction from RLOP

Hu et al. (2025) note a key distinction: Deep Hedging may implicitly allow a speculative component in its hedging policy, because its objective function does not strictly enforce capital preservation. In contrast, [[rlop-model]]'s [[shortfall-probability]] objective explicitly promotes downside-sensitive hedging without speculative upside. Francois et al. (2025) investigated whether the difference between deep hedging and [[delta-hedging]] constitutes a statistical arbitrage. [Source: ssrn-6339420.pdf]

## Role in the Literature

Deep Hedging occupies a middle ground between:
- **Traditional [[delta-hedging]]**: Model-based, no cost optimization, analytically tractable
- **[[qlbs-model]]**: RL-based but backward-looking and value-based
- **[[rlop-model]]**: RL-based, forward-looking, shortfall-aware

It demonstrated the feasibility of neural network-based hedging policies and opened the door for subsequent work (including QLBS extensions and RLOP) that refined the objective functions and training procedures.

## Connections

- **Authors**: Buehler, Gonon, Teichmann & Wood (2019)
- **Extended by**: Hu et al. (2025) who compare it unfavorably on shortfall probability
- **Related work**: Francois et al. (2025) on deep hedging vs. statistical arbitrage

## Cross-References

- [[reinforcement-learning-hedging]] — the broader field
- [[qlbs-model]] — backward value-based alternative
- [[rlop-model]] — forward replication-based alternative with shortfall awareness
- [[delta-hedging]] — traditional approach all RL methods improve upon
