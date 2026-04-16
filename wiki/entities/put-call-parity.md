---
title: Put-Call Parity
type: entity
tags: [options-pricing, arbitrage, put-call-parity, borrow-fees]
sources: [ssrn-4953435.pdf, 1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Put-Call Parity

## Description

Put-call parity is a fundamental relationship in options pricing that links the prices of European call and put options with the same strike price and expiration on the same underlying asset. It is a no-arbitrage condition that must hold in efficient markets (up to transaction costs and frictions).

## Standard Formula

P(S,t) = K*e^{-r(T-t)} - S + C(S,t)

Or equivalently:

C - P = S - K*e^{-r(T-t)}

where C is the call price, P is the put price, S is the stock price, K is the strike price, r is the risk-free rate, and T-t is time to expiration. [Source: ssrn-4953435.pdf]

## With Borrow Fees

When the stock has a borrow fee h, the parity relation becomes:

C - P = e^{-h(T-t)} * S - e^{-r(T-t)} * K

The borrow fee enters because a synthetic long stock position (long call, short put) no longer has the same cost as holding actual stock when the stock can be lent out for a fee. Violations of the standard (h=0) put-call parity are often attributed to informed trading, but Muravyev, Pearson & Pollet (2025) show they more directly reflect the omitted borrow fee. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Role in the Literature

### Borrow Fee Discovery

The put-call parity relation with borrow fees provides the theoretical foundation for extracting [[stock-borrow-fees]] from options prices. By comparing observed call and put prices (or their implied volatilities), one can back out the market's implied borrow fee. Muravyev et al. (2022) show that option-implied borrow fees match actual fees on average. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### IV Spread Explanation

The key insight of Muravyev, Pearson & Pollet (2025) is that when [[implied-volatility]] is computed assuming h=0, the resulting call and put IVs will differ from each other and from the true stock volatility. A first-order Taylor expansion shows:

sigma_C - sigma_P ≈ -sqrt(2*pi*(T-t)) * exp(d1^2/2) * h

This means the entire [[iv-spread-and-skew]] is a direct consequence of ignoring the borrow fee in put-call parity. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### Pairs Trading Foundation

In the [[volatility-pairs-trading]] framework, put-call parity is used to express the put price in terms of the call price, simplifying the construction of the long-short options portfolio to depend only on call option prices and thus only on the volatility differential. [Source: ssrn-4953435.pdf]

## Connections

- Put-call parity violations have historically been studied as indicators of market inefficiency or informed trading. The borrow fee explanation provides a more parsimonious account.
- The relationship is exact for European options and approximate for American options (due to early exercise premium).
- Ofek et al. (2004) showed a strong correlation between put-call parity violations and the cost of short selling, an early hint at the borrow fee explanation.

## Cross-References

- [[black-scholes-model]]
- [[implied-volatility]]
- [[iv-spread-and-skew]]
- [[stock-borrow-fees]]
