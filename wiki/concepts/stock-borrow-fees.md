---
title: Stock Borrow Fees
type: concept
tags: [short-selling, borrow-fees, options-pricing, market-friction]
sources: [1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Stock Borrow Fees

## Definition

Stock borrow fees (also called securities lending fees or stock lending fees) are the costs paid by short sellers to borrow shares from long-side investors. The fee is expressed as an annualized percentage of the position value and accrues daily. It is one of the most important frictions in equity and options markets, yet it is often overlooked in academic research and trading system design. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## How the Borrowing Market Works

Three groups of participants:
1. **Lenders**: Mutual funds, pension funds, insurance companies -- who lend through agent lenders (custodians).
2. **Borrowers**: Hedge funds, proprietary trading desks, option market makers.
3. **Prime brokers**: Intermediaries who borrow from lenders and relend to short sellers at a markup.

The borrow fee is not directly quoted but derived from the "rebate rate" -- the interest rate paid on the cash collateral posted by the borrower. The borrow fee = short-term interest rate - rebate rate. Fees can be negative (rare) or exceed 100% annualized for hard-to-borrow stocks. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Fee Distribution

Using Markit data (2006-2020) for optionable US stocks:

| Percentile | Borrow Fee (annualized) |
|-----------|------------------------|
| Median | 0.4% |
| 90th | 1.5% |
| 99th | 25.7% |
| Mean | 1.5% |

Approximately 11% of stock-day observations have borrow fees greater than 1% per year. These "high-fee" stocks are disproportionately important for understanding options market signals. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Impact on Options Pricing

### The Borrow Fee in Black-Scholes

In the [[black-scholes-model]] with borrow fees, the fee h plays the same role as a continuous dividend. It lowers the expected return on the stock under the risk-neutral measure:

C(S,sigma,r,h,K,t,T) = e^{-h(T-t)} * S * N(d1) - e^{-r(T-t)} * K * N(d2)

where d1 = [ln(S/K) + (r - h + 0.5*sigma^2)(T-t)] / (sigma * sqrt(T-t))

When h > 0 but IV is computed as if h = 0, call IV is understated and put IV is overstated relative to true stock volatility. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### Link to IV Spread and Skew

The implied volatility spread is approximately proportional to the borrow fee:

sigma_C - sigma_P ≈ -sqrt(2*pi*(T-t)) * exp(d1^2/2) * h

This means the entire [[iv-spread-and-skew]] literature may reflect borrow fees rather than informed trading. [Source: 1-s2.0-S0304405X25001618-main.pdf]

### Extracting Borrow Fees from Options

The option-implied borrow fee can be estimated as:

h^implied ≈ -(sigma_C - sigma_P) / sqrt(2*pi*(T-t))

For Tesla, this estimate has a 0.97 correlation with the actual Markit borrow fee. This provides a practical way to estimate borrow costs from publicly available options data. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Impact on Trading Strategies

- The borrow fee is one of the strongest predictors of stock returns. Portfolios sorted by borrow fee show long-short returns of -1.00% per month (t-statistic -3.42). [Source: 1-s2.0-S0304405X25001618-main.pdf]
- After adjusting for borrow fees, the abnormal returns from IV spread-sorted and IV skew-sorted portfolios largely disappear. Long-short spread-sorted returns drop from 0.64% to 0.10%; skew-sorted from 0.54% to 0.17%. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- Excluding high-fee stocks (>1% annual fee) reduces the apparent predictability of IV spread by at least two-thirds. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- Institutional transaction costs (price impact, commissions) further erode any remaining profits from options-based stock return strategies. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Relevance to Our System

- Our options flow analyst should extract implied borrow fees from the IV spread to identify hard-to-borrow stocks.
- Any bearish signal on a high-borrow-fee stock should be treated with skepticism -- the expected return impact may already be priced into options.
- The borrow fee should be factored into any strategy involving short stock positions or short-biased options strategies.
- See [[iv-spread-skew-signals]] for implementation recommendations.

## Cross-References

- [[iv-spread-and-skew]]
- [[implied-volatility]]
- [[put-call-parity]]
- [[black-scholes-model]]
- [[iv-spread-skew-signals]]
