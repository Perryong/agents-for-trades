---
title: Volatility Pairs Trading
type: concept
tags: [options, pairs-trading, volatility, arbitrage]
sources: [ssrn-4953435.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Volatility Pairs Trading

## Definition

Volatility pairs trading is a strategy that constructs long-short portfolios of options on two co-moving securities, where profitability depends solely on the difference in their volatilities (the "volatility residual"). Unlike traditional pairs trading in equities (which bets on price convergence), volatility pairs trading bets on the convergence or divergence of the volatility differential between paired assets. [Source: ssrn-4953435.pdf]

## How It Works

### Portfolio Construction

Given two securities S and Z that move with the same Brownian motion (i.e., same industry, similar exposure to exogenous shocks), construct a portfolio:

pi = C_S/K_S - C_Z/K_Z

where C_S and C_Z are call options on S and Z respectively, with the same moneyness (S/K ratio) and time to expiration. Under the [[black-scholes-model]], this portfolio's value depends only on the volatilities sigma (of S) and varsigma (of Z). [Source: ssrn-4953435.pdf]

### Volatility Residual

The volatility residual is defined as:

Vol_epsilon_t = sigma_t - varsigma_t

This is the key variable to forecast. If you can predict whether the volatility residual will increase or decrease, you can construct a profitable trade. [Source: ssrn-4953435.pdf]

### Trading Rules (Moneyness > 1)

When the expected volatility residual is expected to **decrease** (E[sigma] < E[varsigma]):
- Buy a Call on asset S with moneyness M and expiration T
- Sell a Call on asset Z with moneyness M and expiration T

When the expected volatility residual is expected to **increase** (E[sigma] > E[varsigma]):
- Sell a Call on asset S with moneyness M and expiration T
- Buy a Call on asset Z with moneyness M and expiration T

[Source: ssrn-4953435.pdf]

### Role of Moneyness

The profitability surface changes dramatically with moneyness:
- **M > 1 (ITM)**: Profitability is monotonically increasing with the volatility spread. Clean signal, easy to trade.
- **M near 1 (ATM)**: Fragile; small moves can tip moneyness across the boundary, reversing the trade direction.
- **M < 1 (OTM)**: Highly non-linear; the relationship between volatility differential and profit is complex.

The authors recommend focusing on ITM options (M > 1) for pairs trading. [Source: ssrn-4953435.pdf]

## Empirical Evidence

- Microstructure factors (Roll measure, price dispersion, price impact, realized volatility) exhibit persistence and can predict the volatility residual one day ahead using OLS regression. [Source: ssrn-4953435.pdf]
- Adjusted R-squared values for futures pairs range from 0.05 to 0.224, with equities showing lower but still significant values. [Source: ssrn-4953435.pdf]
- Tested pairs include OXY-XOM and MSFT-GOOGL for equities, and various futures pairs (SPY/GC=F, SPY/ZB=F, etc.). [Source: ssrn-4953435.pdf]

## Relevance to Our System

This concept forms the foundation of the [[options-pairs-trading-strategy]]. Our system could implement this by:
1. Identifying co-moving pairs using correlation analysis
2. Computing daily [[microstructure-effects]] from OHLC data
3. Running OLS regressions to predict the volatility residual
4. Executing the appropriate long-short option trade

## Cross-References

- [[options-pairs-trading-strategy]]
- [[implied-volatility]]
- [[microstructure-effects]]
- [[black-scholes-model]]
- [[improve-volatility-analyst]]
