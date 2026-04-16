---
title: "Managing Volatility for Profitable Options Trading: Evidence from Pairs Trading Strategies"
type: source
tags: [options, pairs-trading, volatility, microstructure, OLS, neural-networks]
sources: [ssrn-4953435.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Managing Volatility for Profitable Options Trading: Evidence from Pairs Trading Strategies

## Citation

Aldridge, I. & Jiang, K. (2024). Managing Volatility for Profitable Options Trading: Evidence from Pairs Trading Strategies. *Preprint submitted to Elsevier*, September 11, 2024. Cornell University ORIE / AbleMarkets.

## Abstract Summary

This study introduces a novel methodology for options pairs trading that exploits volatility persistence and [[microstructure-effects]] to generate profitable returns. The authors construct pairwise options portfolios using the [[black-scholes-model]] where profitability depends solely on the volatility differential (the "volatility residual") between two co-moving securities. They demonstrate that [[microstructure-effects]] such as bid-ask bounce, price dispersion, price impact, and realized volatility significantly influence the volatility spread and can be used to predict it. Critically, simple OLS linear regressions outperform neural networks for this application. [Source: ssrn-4953435.pdf]

## Key Findings

- **Volatility residual drives profit**: For a pair of options on co-moving securities with the same moneyness and expiration, the portfolio profit depends solely on the difference in volatilities (the "volatility residual", defined as sigma_t - varsigma_t). [Source: ssrn-4953435.pdf]
- **Moneyness matters**: For in-the-money options (M > 1), profitability is monotonically increasing with decreasing volatility of asset S and increasing volatility of asset Z. For near-the-money options, the payoff surface is highly non-linear and fragile. [Source: ssrn-4953435.pdf]
- **Microstructure factors predict volatility**: Four microstructure variables -- Roll measure (bid-ask bounce proxy), price dispersion, price impact, and realized volatility -- have statistically significant explanatory power for the volatility residual. [Source: ssrn-4953435.pdf]
- **Persistence enables trading**: Microstructure effects exhibit persistence over time, allowing one-day-ahead forecasts of volatility residuals to generate profitable trading signals. [Source: ssrn-4953435.pdf]
- **OLS outperforms neural networks**: Simple OLS linear regressions outperform various neural network specifications for predicting volatility residuals in this application. [Source: ssrn-4953435.pdf]
- **Futures show stronger results**: Adjusted R-squared values are much higher for futures pairs (up to 0.224) than equity pairs, implying greater inefficiencies in futures markets. [Source: ssrn-4953435.pdf]
- **Daily data suffices**: Microstructure effects can be successfully proxied using daily Open, High, Low, and Close prices; higher-frequency data does not improve outcomes. [Source: ssrn-4953435.pdf]
- **Empirically validated pairs**: OXY-XOM and MSFT-GOOGL equity pairs were tested empirically with 2-day-ahead rolling window forecasts, confirming theoretical predictions. [Source: ssrn-4953435.pdf]

## Methodology

1. **Theoretical framework**: Construct long-short options portfolio on two co-moving securities using [[black-scholes-model]] with same moneyness (S/K ratio) and expiration. Show portfolio value depends only on volatility differential.
2. **Volatility estimation**: Use range volatility (High - Low) / Open as daily volatility proxy rather than traditional GARCH-type models, to localize data to single trading days.
3. **Microstructure variables**: Compute four daily microstructure metrics -- Roll measure, price dispersion, price impact, realized volatility -- from intraday hourly data for the 2022-2023 period.
4. **Regression**: OLS regression of volatility residual on microstructure variables for each pair. Compared against neural network alternatives.
5. **Trading simulation**: 2-day-ahead rolling window forecasts; buy/sell option pairs at close on day t, reverse at close on day t+1.

## Relevance to AI Trading System

- The finding that OLS outperforms neural networks is a cautionary lesson for our system: simpler models may be preferable for volatility forecasting tasks.
- The microstructure variables (Roll measure, price dispersion, price impact, realized volatility) could be incorporated into our [[implied-volatility]] analysis pipeline.
- The [[volatility-pairs-trading]] strategy could be implemented as a new strategy module.
- Daily OHLC data is sufficient for computing these microstructure proxies, meaning no expensive tick data is needed.

## Cross-References

- [[implied-volatility]]
- [[volatility-pairs-trading]]
- [[microstructure-effects]]
- [[black-scholes-model]]
- [[options-pairs-trading-strategy]]
- [[improve-volatility-analyst]]
