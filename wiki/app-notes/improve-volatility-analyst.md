---
title: "App Note: Improve Volatility Analyst with Microstructure Factors"
type: app-note
tags: [volatility-analyst, microstructure, feature-engineering, OLS]
sources: [ssrn-4953435.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Improve Volatility Analyst with Microstructure Factors

## What to Change

Add [[microstructure-effects]] as features to our volatility analyst agent's forecasting pipeline. Specifically, compute the following four variables from daily OHLC data for each asset under analysis:

1. **Range Volatility**: (High - Low) / Open -- a single-day volatility proxy that avoids contamination from other trading days. [Source: ssrn-4953435.pdf]
2. **Roll Measure**: 2 * sqrt(-cov(Delta_P_t, Delta_P_{t-1})) -- a bid-ask spread proxy computed from consecutive price changes. [Source: ssrn-4953435.pdf]
3. **Price Impact**: (1/T) * sum(|Delta_P| / V) -- measures price sensitivity to order flow. [Source: ssrn-4953435.pdf]
4. **Price Dispersion**: sqrt(sum(w_t * (P_t - EP_t)^2)) -- volume-weighted intraday price variability. [Source: ssrn-4953435.pdf]

## Why (with Source Citation)

Aldridge & Jiang (2024) demonstrate that these microstructure variables:
- Have statistically significant explanatory power for volatility spreads between paired assets (regression results in Tables 1-3 of the paper). [Source: ssrn-4953435.pdf]
- Exhibit **persistence**, meaning today's values predict tomorrow's volatility outcomes. This persistence is the key property that makes them useful for trading signals. [Source: ssrn-4953435.pdf]
- Can be computed entirely from **daily OHLC data** -- no expensive tick data or intraday feeds required. The paper specifically notes that higher-frequency data does not improve volatility prediction outcomes. [Source: ssrn-4953435.pdf]
- Simple **OLS regression outperforms neural networks** for this application, suggesting that our volatility analyst should not over-engineer the model. [Source: ssrn-4953435.pdf]

## Expected Impact

- **Better volatility forecasts**: Adding microstructure features should improve our system's ability to predict near-term volatility changes, especially for pairs and relative-value analysis.
- **New strategy capability**: Enables the [[options-pairs-trading-strategy]] which requires accurate volatility residual predictions.
- **Reduced complexity**: The OLS finding argues against adding neural network layers for volatility prediction, potentially simplifying our agent architecture.
- **Low implementation cost**: Requires only daily OHLC data, which we already have from yfinance.

## Implementation Notes

### Data Requirements

- Daily OHLC + Volume for each ticker (already available via yfinance).
- For the Roll measure, need at least 2 consecutive days of price changes.
- For price dispersion and price impact, hourly intraday data is ideal but daily proxies can be constructed:
  - Price dispersion can be approximated from the OHLC range and volume.
  - Price impact can be approximated as (High - Low) / Volume.

### Where to Integrate

- **Volatility analyst agent** (`tradingagents/agents/analysts/technical_analyst.py` or a dedicated volatility module): Add microstructure feature computation to the analysis pipeline.
- **Feature store**: Compute and cache these features daily for all tickers in the watchlist.
- **Prediction model**: Use a simple OLS regression (e.g., scikit-learn LinearRegression) rather than LLM-based reasoning for the quantitative volatility forecast.

### Suggested Approach

1. Add a `compute_microstructure_features(ticker, lookback_days)` function that returns the four variables.
2. For pairs analysis, compute the **difference** of each microstructure variable between the two assets.
3. Fit OLS regression: Vol_residual = alpha + beta_1*Roll_diff + beta_2*PD_diff + beta_3*PI_diff + beta_4*RV_diff + epsilon.
4. Use rolling estimation window (e.g., 60 trading days) for coefficient estimation.
5. Forecast one-day-ahead volatility residual and generate trading signal.

## Cross-References

- [[microstructure-effects]]
- [[volatility-pairs-trading]]
- [[options-pairs-trading-strategy]]
- [[implied-volatility]]
