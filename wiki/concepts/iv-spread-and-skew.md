---
title: IV Spread and Skew
type: concept
tags: [implied-volatility, options, stock-returns, borrow-fees, put-call-parity]
sources: [1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# IV Spread and Skew

## Definition

### Implied Volatility Spread

The IV spread is the difference between call and put [[implied-volatility]] for options on the same underlying with the same strike and expiration. Two common versions:

- **Surface spread**: Difference between the 30-day ATM call IV and 30-day ATM put IV from the volatility surface. Mean value approximately -0.31%. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **CW spread** (Cremers & Weinbaum, 2010): Open-interest weighted average of IV differences across put-call pairs from option price files. Mean value approximately -0.70%. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### Implied Volatility Skew

The IV skew measures the difference between OTM put IV and ATM call IV:

- **Surface skew**: OTM (Delta=-0.25) put IV minus ATM (Delta=-0.5) call IV. Mean approximately +0.058. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **XZZ skew** (Xing et al., 2010): OTM (70-95%) put IV minus ATM (95-105%) call IV. Mean approximately -0.039. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## The Borrow Fee Connection

The central finding of Muravyev, Pearson & Pollet (2025) is that the IV spread and skew are largely proxies for [[stock-borrow-fees]] rather than indicators of informed trading.

### Theoretical Relationship

When IVs are computed assuming zero borrow fees (standard practice), the resulting IV spread is proportional to the omitted borrow fee h:

sigma_C - sigma_P ≈ -sqrt(2*pi*(T-t)) * exp(d1^2/2) * h

For near-the-money options, this simplifies to:

h^implied ≈ -(sigma_C - sigma_P) / sqrt(2*pi*(T-t))

The skew similarly reflects the borrow fee because it can be decomposed into the spread and the difference between OTM and ATM put implied volatilities. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### Empirical Evidence

- The IV spread is strongly negatively correlated with the borrow fee: -0.24 for surface spread, -0.31 for CW spread. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- For Tesla, the correlation between the option-implied borrow fee and the actual Markit borrow fee is 0.97. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- Sorting stocks into deciles by IV spread produces long-short returns of 0.64% per month (t=5.94) before fee adjustment, but only an insignificant 0.10% (t=0.92) after. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- Decile one (lowest spread) has 83.5 high-fee stocks on average (borrow fee >1%) with average fee of 6.86% per year. Decile ten has only 33.1 with average fee of 1.26%. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Traditional Interpretation (Now Challenged)

Prior literature (Bali & Hovakimian 2009; Cremers & Weinbaum 2010; Xing et al. 2010) interpreted the predictive power of IV spread and skew as evidence that:
- Informed traders prefer the options market
- Options prices incorporate information slowly
- Stock prices are inefficient with respect to options market information

Muravyev et al. (2025) challenge this interpretation: the predictability comes from the borrow fee, not informed trading. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Relevance to Our System

- **Do not use IV spread/skew as pure directional signals**: Their predictive power largely reflects borrow fees, not informed trading. Treat them as borrow fee proxies instead.
- **Use as borrow fee estimators**: The option-implied borrow fee formula provides free access to borrow cost estimates without expensive lending market data.
- **Flag high-fee stocks**: When IV spread is very negative (large gap between put and call IV), the stock likely has high borrow fees and short-selling constraints.
- See [[iv-spread-skew-signals]] for specific implementation recommendations.

## Cross-References

- [[implied-volatility]]
- [[stock-borrow-fees]]
- [[put-call-parity]]
- [[iv-spread-skew-signals]]
