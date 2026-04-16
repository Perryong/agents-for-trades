---
title: Implied Volatility
type: concept
tags: [options, volatility, pricing, greeks]
sources: [ssrn-4953435.pdf, losing_optional.pdf, 1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Implied Volatility

## Definition

Implied volatility (IV) is the market's forecast of the likely magnitude of a security's price movement, extracted by inverting an options pricing model (typically the [[black-scholes-model]]). It represents the volatility value that, when plugged into the pricing formula, produces the observed market price of an option.

Unlike historical (realized) volatility which measures past price movements, IV is forward-looking and embedded in current option prices.

## Key Concepts

### IV vs Historical Volatility (HV)

- **IV** reflects market expectations of future volatility, incorporating supply/demand dynamics for options.
- **HV** (also called realized volatility) measures the standard deviation of past returns over a specified period. [Source: ssrn-4953435.pdf]
- The difference between IV and HV is sometimes called the "volatility risk premium" and is on average positive, meaning options tend to be priced above subsequently realized volatility. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### IV Rank and IV Percentile

- **IV Rank**: Where current IV falls relative to its range over a lookback period. IV Rank = (Current IV - 52-week Low IV) / (52-week High IV - 52-week Low IV).
- **IV Percentile**: The percentage of days in the lookback period where IV was below the current level.

### Implied Volatility and Borrow Fees

A critical finding from Muravyev, Pearson & Pollet (2025) is that standard IV calculations from vendors like OptionMetrics assume a zero [[stock-borrow-fees]], which creates systematic distortions. When the borrow fee h > 0, call IV is understated and put IV is overstated relative to the true stock volatility sigma. This creates an artificial [[iv-spread-and-skew]] that is proportional to the borrow fee. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### Implied Volatility Around Earnings

Implied volatility exhibits a characteristic pattern around earnings announcements. Short-dated IV rises sharply before earnings (reflecting the expected jump) while longer-dated IV remains relatively stable. The difference, termed [[expected-announcement-volatility]] (AbnormalIV), measures the market's expectation of the earnings-day price move. Retail investors are drawn to buy options when this measure is high. [Source: losing_optional.pdf]

## Empirical Evidence

- In the top quintile of retail option purchases prior to high-EAV announcements, option-implied variances escalate by 40% more in the days immediately prior to the announcement. [Source: losing_optional.pdf]
- The IV spread (call IV minus put IV) has a correlation of -0.24 with the indicative borrow fee (negative because higher borrow fee lowers call IV relative to put IV when computed assuming zero fees). [Source: 1-s2.0-S0304405X25001618-main.pdf]
- Range volatility computed from daily OHLC prices is an effective proxy for realized volatility and can capture microstructure effects. [Source: ssrn-4953435.pdf]

## Relevance to Our System

- IV is a core input to our volatility analyst and options flow analyst.
- Our system should be aware that IV from standard data vendors may be distorted by omitted borrow fees, especially for hard-to-borrow stocks.
- The EAV metric (AbnormalIV) is a computable signal for our earnings screener.
- IV differentials between paired securities form the basis of the [[volatility-pairs-trading]] strategy.

## Cross-References

- [[iv-spread-and-skew]]
- [[expected-announcement-volatility]]
- [[stock-borrow-fees]]
- [[black-scholes-model]]
- [[microstructure-effects]]
