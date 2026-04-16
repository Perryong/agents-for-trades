---
title: Black-Scholes Model
type: entity
tags: [options-pricing, model, volatility, greeks]
sources: [ssrn-4953435.pdf, losing_optional.pdf, 1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Black-Scholes Model

## Description

The Black-Scholes (or Black-Scholes-Merton) model is the foundational framework for pricing European-style options. Published by Fischer Black, Myron Scholes, and Robert Merton in 1973, it provides a closed-form solution for option prices under specific assumptions about the underlying asset's price dynamics.

## Core Formulas

### Standard Black-Scholes (no borrow fee)

Call price: C(S,t) = S*N(d+) - K*e^{-r(T-t)}*N(d-)

where:
- d+ = [ln(S/K) + (r + sigma^2/2)(T-t)] / (sigma*sqrt(T-t))
- d- = d+ - sigma*sqrt(T-t)
- N(.) = standard normal CDF
- S = stock price, K = strike, r = risk-free rate, sigma = volatility, T-t = time to expiration

[Source: ssrn-4953435.pdf]

### With Borrow Fee

When the stock has a borrow fee h (analogous to a continuous dividend):

C(S,sigma,r,h,K,t,T) = e^{-h(T-t)} * S * N(d1) - e^{-r(T-t)} * K * N(d2)

P(S,sigma,r,h,K,t,T) = -e^{-h(T-t)} * S * N(-d1) + e^{-r(T-t)} * K * N(-d2)

where d1 = [ln(S/K) + (r - h + 0.5*sigma^2)(T-t)] / (sigma*sqrt(T-t))

The borrow fee h lowers the expected return on the stock under the risk-neutral measure, exactly as a continuous dividend would. Standard academic data vendors (e.g., OptionMetrics pre-July 2024) compute implied volatilities assuming h = 0, which creates systematic distortions in the [[iv-spread-and-skew]]. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Role in the Literature

### Volatility Pairs Trading (Aldridge & Jiang 2024)

The [[volatility-pairs-trading]] strategy uses Black-Scholes to construct pairwise options portfolios that are dependent only on market volatility. By matching moneyness (S/K ratio) and expiration across a pair, the portfolio value reduces to a function of the two assets' volatilities alone. [Source: ssrn-4953435.pdf]

### EAV Measurement (de Silva, So & Smith 2026)

The AbnormalIV metric used to measure [[expected-announcement-volatility]] is derived from Black-Scholes implied variances at different maturities in OptionMetrics. [Source: losing_optional.pdf]

### Borrow Fee Extraction (Muravyev, Pearson & Pollet 2025)

A Taylor expansion of the Black-Scholes model around h=0 reveals that the [[iv-spread-and-skew]] is proportional to the [[stock-borrow-fees]], providing a formula for extracting borrow fees from options prices. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Key Assumptions and Limitations

- Assumes geometric Brownian motion (constant volatility) -- violated in practice by volatility clustering, jumps, and stochastic volatility.
- Assumes European exercise -- US equity options are American-style, introducing early exercise considerations.
- Assumes no dividends (or continuous dividends) and no borrow fees in the standard version.
- The model remains the benchmark for [[implied-volatility]] calculation despite its known limitations.

## Cross-References

- [[implied-volatility]]
- [[put-call-parity]]
- [[iv-spread-and-skew]]
- [[stock-borrow-fees]]
- [[volatility-pairs-trading]]
