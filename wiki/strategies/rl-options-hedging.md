---
title: RL Options Hedging Strategy
type: strategy
tags: [strategy, reinforcement-learning, options-hedging, RLOP, QLBS]
sources: [ssrn-6339420.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Overview

A practical strategy for hedging short option positions using reinforcement learning agents instead of traditional [[delta-hedging]]. Based on the RLOP and Adaptive-QLBS frameworks from Hu et al. (2025), this strategy optimizes for [[shortfall-probability]] rather than replication accuracy, delivering superior after-cost outcomes especially during market stress. [Source: ssrn-6339420.pdf]

## Setup Conditions

- **Instruments**: European-style call options on liquid underlyings (ETFs preferred: SPY, XOP, or similar)
- **Maturity range**: 3-70 calendar days (validated); primary focus on 14-56 day buckets
- **Moneyness**: ATM (K/F = 1) and mildly OTM (K/F = 1.03) validated
- **Rebalancing**: Daily
- **Cost structure**: Proportional transaction costs (half-spread or commission rate)

[Source: ssrn-6339420.pdf]

## Entry Rules

1. Sell (short) the call option and collect premium
2. Initialize a self-financing hedging portfolio with the option premium
3. Select the RL model based on desk objective:
   - **[[qlbs-model]]** for cost-minimization priority (stabilizer role)
   - **[[rlop-model]]** for shortfall-minimization priority (capital preservation)
4. Calibrate/train the RL agent on the same-day option cross-section

[Source: ssrn-6339420.pdf]

## Ongoing Management

1. Each trading day, the RL agent observes the normalized state (t, X_t) or (t, S_t)
2. Agent outputs the optimal hedge position (shares of underlying)
3. Rebalance the portfolio to match the agent's recommended position
4. Track cumulative transaction cost TC_T and before-cost replication component xi_T
5. Monitor the risk-cost map position: E[TC_T] vs RMSE(xi_T)

[Source: ssrn-6339420.pdf]

## Exit Rules

- At maturity T, the terminal stock position is marked to market without explicit closing trade
- Net hedging outcome: PnL_T^net = W_T - (S_T - K)^+
- Evaluate shortfall: SF_T = max(0, -PnL_T^net)

[Source: ssrn-6339420.pdf]

## Position Sizing / Risk Management

- **Model selection framework**: Use the bidirectional cost-risk map to select between QLBS and RLOP based on the current regime and desk constraints. [Source: ssrn-6339420.pdf]
- **Regime awareness**: During stress periods (high VIX, sector dislocations), prefer RLOP for its superior tail-risk properties. During calm periods, either model is competitive. [Source: ssrn-6339420.pdf]
- **Risk aversion parameter lambda**: Higher values produce more conservative (and more expensive) hedging. Tune to desk risk tolerance. [Source: ssrn-6339420.pdf]

## Historical Evidence

| Setting | Best Shortfall Prob. | Best ES_5% | Best ES_10% |
|---------|---------------------|-----------|------------|
| SPY 2020Q1 ATM | RLOP (0.91) | BS (8.787) | BS (8.395) |
| SPY 2020Q1 OTM | QLBS (7.538) | QLBS (7.271) | SV (0.96) |
| XOP 2020Q1 ATM | RLOP (0.55) | RLOP (0.694) | RLOP (0.674) |
| XOP 2020Q1 OTM | RLOP (0.78) | RLOP (0.502) | RLOP (0.489) |
| XOP 2025Q2 ATM | RLOP (0.39) | QLBS (4.610) | BS (2.983) |
| XOP 2025Q2 OTM | RLOP (0.33) | QLBS (3.037) | QLBS (2.075) |

RLOP dominates shortfall probability; RL methods dominate the stress regime (XOP 2020Q1). [Source: ssrn-6339420.pdf]

## Limitations

- Requires daily retraining/recalibration on current option cross-section
- Computational cost of Monte Carlo rollouts for RLOP training
- Not yet validated for path-dependent or American-style options
- Performance on very short-dated (< 3 day) or long-dated (> 70 day) options untested

## Cross-References

- [[reinforcement-learning-hedging]] — conceptual foundation
- [[rlop-model]] / [[qlbs-model]] — the two RL models
- [[delta-hedging]] — traditional approach this strategy replaces
- [[rl-hedging-for-greeks-monitor]] — how to integrate into our app
