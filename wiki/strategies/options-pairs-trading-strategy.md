---
title: Options Pairs Trading Strategy
type: strategy
tags: [options, pairs-trading, volatility, microstructure, mean-reversion]
sources: [ssrn-4953435.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Options Pairs Trading Strategy

## Overview

A volatility-based pairs trading strategy that exploits persistent [[microstructure-effects]] to predict the volatility differential between two co-moving securities, then trades in-the-money options to profit from the predicted change. Based on Aldridge & Jiang (2024). [Source: ssrn-4953435.pdf]

## Setup Conditions

1. **Identify co-moving pairs**: Select two securities in the same industry or exposed to the same systematic factors (e.g., OXY-XOM, MSFT-GOOGL for equities; SPY-GC=F for cross-asset futures). The pair should exhibit historical price co-movement driven by a shared Brownian motion.
2. **Ensure options liquidity**: Both securities must have liquid options with matching moneyness and expiration dates available.
3. **Focus on ITM options**: Use options with moneyness M > 1 (S/K > 1 for calls). The profitability surface is monotonic and well-behaved for ITM options; near-the-money options are fragile. [Source: ssrn-4953435.pdf]

## Entry Rules

### Signal Generation

1. Compute daily [[microstructure-effects]] for each asset in the pair:
   - **Range Volatility**: (High - Low) / Open
   - **Roll Measure**: 2 * sqrt(-cov(Delta_P_t, Delta_P_{t-1})) -- proxy for bid-ask spread
   - **Price Dispersion**: Volume-weighted standard deviation of intraday prices
   - **Price Impact**: Average absolute price change per unit of volume
   - **Realized Volatility**: Standard deviation of intraday returns
2. Compute the **volatility residual**: Vol_epsilon_t = RangeVol_S,t - RangeVol_Z,t
3. Run OLS regression of volatility residual on lagged microstructure variables for both assets (use rolling estimation window).
4. Forecast next-day volatility residual E[Vol_epsilon_{t+1}].

### Trade Execution

**If E[Vol_epsilon_{t+1}] < 0** (expect S volatility to fall relative to Z):
- Buy a Call on asset S with moneyness M > 1 and expiration T
- Sell a Call on asset Z with moneyness M > 1 and expiration T

**If E[Vol_epsilon_{t+1}] > 0** (expect S volatility to rise relative to Z):
- Sell a Call on asset S with moneyness M > 1 and expiration T
- Buy a Call on asset Z with moneyness M > 1 and expiration T

Execute at close on day t. [Source: ssrn-4953435.pdf]

## Exit Rules

- Reverse position at close on day t+1 (one-day holding period in the original study).
- Could be extended to longer holding periods with appropriate position management.
- Stop-loss should be based on the maximum tolerable loss from the combined option position.

## Position Sizing

- Normalize positions by strike price: trade C_S/K_S - C_Z/K_Z to make the position comparable across different price levels.
- Scale by available capital and risk tolerance; the strategy involves both long and short option positions.

## Risk Management

- **Model risk**: OLS regression coefficients vary across pairs; the model may break down during regime changes.
- **Execution risk**: Bid-ask spreads on options can erode profits. Use limit orders and avoid illiquid option series.
- **Moneyness drift**: Monitor that both options remain ITM throughout the holding period. Near-ATM options create instability.
- **Correlation breakdown**: The fundamental assumption is co-movement; if the pair decorrelates, the strategy can produce large losses.
- **Transaction costs**: Factor in round-trip option bid-ask spreads for both legs.

## Historical Evidence

- OLS models achieve adjusted R-squared of 0.05-0.224 for predicting volatility residuals one day ahead, with futures pairs showing stronger results than equity pairs. [Source: ssrn-4953435.pdf]
- Neural networks did not improve upon OLS performance, suggesting the relationship is approximately linear. [Source: ssrn-4953435.pdf]
- Empirical testing on OXY-XOM and MSFT-GOOGL pairs with 2-day-ahead rolling window forecasts confirmed theoretical predictions. [Source: ssrn-4953435.pdf]

## Key Insight: Keep It Simple

The finding that OLS outperforms neural networks is significant for implementation. Do not over-engineer the volatility prediction model. A simple linear regression on microstructure variables computed from daily OHLC data is sufficient and more robust than complex ML approaches for this specific application. [Source: ssrn-4953435.pdf]

## Cross-References

- [[volatility-pairs-trading]]
- [[microstructure-effects]]
- [[implied-volatility]]
- [[black-scholes-model]]
- [[improve-volatility-analyst]]
