---
title: Microstructure Effects
type: concept
tags: [microstructure, liquidity, bid-ask-spread, price-impact, volatility]
sources: [ssrn-4953435.pdf, 1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Microstructure Effects

## Definition

Market microstructure effects are phenomena arising from the mechanics of how securities are traded -- order flow, bid-ask dynamics, price impact of trades, and information transmission through the trading process. These effects account for a substantial portion of observed asset volatility and are distinct from "fundamental" volatility driven by news or economic factors. [Source: ssrn-4953435.pdf]

## Key Microstructure Variables

### Bid-Ask Bounce (Roll Measure)

The tendency of transaction prices to oscillate between bid and ask prices, creating a negative autocovariance in price changes. The Roll measure estimates the effective bid-ask spread from transaction data:

Roll_t = 2 * sqrt(-cov(Delta_P_t, Delta_P_{t-1}))

This reverses the typical negative covariance caused by the bid-ask bounce. Higher Roll values indicate wider effective spreads and lower liquidity. [Source: ssrn-4953435.pdf]

### Price Dispersion

A volume-weighted measure of intraday price variability around the daily average:

DP_t = sqrt(sum(w_t * (P_t - EP_t)^2))

where w_t is the volume weight for each trading period. Higher dispersion indicates greater intraday uncertainty and mixed trading signals. [Source: ssrn-4953435.pdf]

### Price Impact

Quantifies the relationship between trading volume and price changes within a day:

IP_t = (1/T) * sum(|Delta_P_t| / V_t)

where Delta_P_t is the high-low range within a trading period and V_t is volume. Higher price impact means the asset is more sensitive to order flow, indicating lower liquidity. [Source: ssrn-4953435.pdf]

### Realized Volatility

The standard deviation of intraday returns:

RealizedVol_t = (1/(T-1)) * sqrt(sum((r_tau - Er_tau)^2))

Captures actual price variability within a trading day. [Source: ssrn-4953435.pdf]

### Range Volatility

A simpler daily volatility proxy using only OHLC data:

RangeVol_t = (High_t - Low_t) / Open_t

This normalization by the Open price allows comparison across assets with different price levels. Importantly, this can be computed from daily data without requiring intraday tick data. [Source: ssrn-4953435.pdf]

## Empirical Evidence

- Microstructure factors significantly influence the volatility spread between paired assets, with statistically significant regression coefficients for most variables. [Source: ssrn-4953435.pdf]
- The signs of microstructure coefficients vary from one asset pair to the next, suggesting that each pair has its own microstructure dynamics. [Source: ssrn-4953435.pdf]
- Microstructure effects can be successfully proxied using daily OHLC prices; higher-frequency data does not improve volatility prediction outcomes. [Source: ssrn-4953435.pdf]
- Option bid-ask spreads are a significant source of noise in implied volatility calculations, particularly for less liquid stocks. Wide option spreads lead to noisy implied borrow fee estimates. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Relevance to Our System

- These four microstructure variables (Roll, price dispersion, price impact, realized volatility) could be computed from daily OHLC data and added as features to our volatility forecasting models.
- The finding that microstructure effects are persistent makes them actionable for next-day trading decisions.
- Our system should account for bid-ask spread costs when evaluating options strategies, as they are a significant drag on returns.

## Cross-References

- [[volatility-pairs-trading]]
- [[implied-volatility]]
- [[improve-volatility-analyst]]
- [[stock-borrow-fees]]
