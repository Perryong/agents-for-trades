---
title: QLBS Model (Q-Learner in Black-Scholes)
type: entity
tags: [model, reinforcement-learning, options-hedging, QLBS, Q-learning]
sources: [ssrn-6339420.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Description

QLBS (Q-Learner in Black-Scholes) is a reinforcement learning framework for option pricing and hedging that formulates the problem as a discrete-time Markov Decision Process. Originally introduced by Igor Halperin (2020) in "QLBS: Q-Learner in the Black-Scholes (-Merton) Worlds" (Journal of Derivatives, 28(1), 99-122), it was the first to cast options hedging as an RL problem with explicit treatment of transaction costs. [Source: ssrn-6339420.pdf]

## Adaptive-QLBS (Hu et al., 2025)

The version studied in Hu et al. (2025) modifies the original QLBS in two key ways:

1. **Filtration-adapted value function**: The value function is redefined so that it becomes adapted to the filtration F_t, resolving a technical issue in the original where the value function was not directly adapted.

2. **Variance stabilization**: Variance terms are replaced with their square roots to obtain a dimensionless, numerically more stable value estimate.

The value function reads:
V_t^pi(X_t) = E_t[-d_T(t) * Pi_t(X_t) - lambda * sum_{tau=t}^{T} gamma^{tau-t} * sqrt(Var|Pi_tau(X_tau)|)]

where d_T(t) = (1 - t/T) is a discounting factor, gamma = e^{-r*dt}, and lambda is the risk-aversion parameter. [Source: ssrn-6339420.pdf]

## Architecture

- **Approach**: Backward, value-based RL
- **State**: Normalized price process X_t = (mu - sigma^2/2)*t + log(S_t)
- **Action**: Hedge position a_t (shares of underlying)
- **Policy**: Gaussian pi = N(mu_pi, sigma_pi), where mu and sigma are produced by a shared ResNet-style architecture
- **Training**: REINFORCE with a learned baseline, Adam optimizer, learning rate 10^-4

[Source: ssrn-6339420.pdf]

## Key Properties

- **Cost-aware stabilizer**: QLBS acts primarily as a cost optimizer, consistently achieving low average trading costs across all tested slices. [Source: ssrn-6339420.pdf]
- **Option price monotonicity**: For sufficiently large transaction cost parameter epsilon, the QLBS option price is monotonically increasing in both risk aversion lambda and friction epsilon. [Source: ssrn-6339420.pdf]
- **Complementary to [[rlop-model]]**: While QLBS prioritizes cost stability, RLOP prioritizes downside control, making them complementary for different desk objectives. [Source: ssrn-6339420.pdf]

## Performance

On SPY and XOP options (28-day maturity):
- Achieves the best ES_5% in 2 of 8 slices (SPY 2020Q1 OTM, XOP 2025Q2 ATM)
- Consistently achieves among the lowest average trading costs
- IVRMSE is competitive with parametric models in calm conditions

[Source: ssrn-6339420.pdf]

## Connections

- **Original author**: Igor Halperin (NYU, 2020)
- **Extended by**: Hu, Chen, Yi & Sun (2025) into Adaptive-QLBS
- **Related**: [[deep-hedging]] (Buehler et al., 2019), [[rlop-model]]

## Cross-References

- [[reinforcement-learning-hedging]] — the broader field
- [[rlop-model]] — complementary forward-looking model
- [[delta-hedging]] — traditional approach QLBS improves upon
