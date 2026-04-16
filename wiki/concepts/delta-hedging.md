---
title: Delta Hedging
type: concept
tags: [options, hedging, Greeks, Black-Scholes, risk-management]
sources: [ssrn-6339420.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Definition

Delta hedging is the traditional approach to managing the directional risk of an options position by holding a position in the underlying asset equal to the option's delta (the partial derivative of the option price with respect to the underlying price). Under the Black-Scholes assumptions of continuous trading, no transaction costs, and known constant volatility, delta hedging perfectly replicates the option payoff. [Source: ssrn-6339420.pdf]

## How It Works

For a short call option position:
1. Calculate the model-implied delta from a parametric pricing model (Black-Scholes, Jump-Diffusion, Heston SV)
2. Hold delta shares of the underlying asset in a self-financing portfolio
3. Rebalance the hedge at discrete intervals (e.g., daily)
4. At maturity, the hedging portfolio should approximate the option payoff

The self-financing constraint requires that rebalancing is funded entirely by the existing portfolio: u_t * S_{t+1} + e^{r*dt} * B_t = u_{t+1} * S_{t+1} + B_{t+1} + TC(u_{t+1} - u_t, S_{t+1}), where TC denotes transaction costs. [Source: ssrn-6339420.pdf]

## Limitations

Hu et al. (2025) demonstrate several fundamental limitations of traditional delta hedging:

1. **Static calibration diverges from dynamic performance**: Models calibrated to match the implied-volatility surface (low IVRMSE) do not necessarily produce better hedging outcomes under transaction costs. Parametric models dominate static fit but RL policies outperform in after-cost hedging. [Source: ssrn-6339420.pdf]

2. **Transaction costs break optimality**: With proportional costs c|delta_t - delta_{t-}|S_t, the theoretical perfection of continuous hedging vanishes. More frequent rebalancing incurs more costs without proportional improvement in replication accuracy. [Source: ssrn-6339420.pdf]

3. **Discrete rebalancing introduces path dependence**: Real-world daily rebalancing means hedging outcomes depend on the specific realized price path, not just terminal values. [Source: ssrn-6339420.pdf]

4. **No shortfall awareness**: Delta hedging optimizes replication accuracy, not loss probability. A hedge can minimize tracking error while still generating frequent net losses after costs. [Source: ssrn-6339420.pdf]

5. **Regime-dependent performance**: During the 2020 COVID crash, parametric delta hedges showed substantially wider outcome dispersion and heavier left tails, especially for sector ETFs (XOP). [Source: ssrn-6339420.pdf]

## Comparison with RL Approaches

| Dimension | Delta Hedging | RL Hedging |
|-----------|--------------|------------|
| Objective | Minimize replication error | Minimize [[shortfall-probability]] or cost |
| Costs | Not optimized for | Incorporated in reward function |
| Calibration | Static (same-day IV fit) | Dynamic (learned from realized paths) |
| Adaptiveness | Model parameters fixed per calibration | Policy adapts to market regime |
| Stress performance | Degrades significantly | RLOP excels during 2020Q1 crash |

[Source: ssrn-6339420.pdf]

## Relevance to Our System

Our system currently provides Greeks-based analysis including delta. Understanding delta hedging's limitations motivates the potential integration of RL-based hedge ratios as described in [[reinforcement-learning-hedging]] and [[rl-hedging-for-greeks-monitor]].

## Cross-References

- [[reinforcement-learning-hedging]] — RL approaches that improve upon delta hedging
- [[shortfall-probability]] — risk measure absent from traditional delta hedging
- [[qlbs-model]] — RL extension of Black-Scholes hedging
- [[rlop-model]] — forward-looking alternative to delta hedging
