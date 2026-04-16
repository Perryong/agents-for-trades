---
title: "Why Does Options Market Information Predict Stock Returns?"
type: source
tags: [implied-volatility, iv-spread, iv-skew, stock-borrow-fees, put-call-parity, options-pricing]
sources: [1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Why Does Options Market Information Predict Stock Returns?

## Citation

Muravyev, D., Pearson, N.D. & Pollet, J.M. (2025). Why Does Options Market Information Predict Stock Returns? *Journal of Financial Economics*, 172, 104153. doi:10.1016/j.jfineco.2025.104153. University of Illinois at Urbana-Champaign / Michigan State University / Canadian Derivatives Institute.

## Abstract Summary

This paper challenges the widely-held interpretation that [[iv-spread-and-skew]] predict stock returns because of informed trading in the options market. Instead, the authors show that the [[implied-volatility]] spread (call IV minus put IV) and skew are proportional to the omitted [[stock-borrow-fees]], which is a major friction preventing arbitrage. When implied volatilities are computed assuming zero borrow fees (as is standard in academic data), the resulting "artificial" IV spread and skew mechanically reflect the true borrow fee. After adjusting for fees, the predictive power of IV spread and skew largely disappears. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Key Findings

- **IV spread proxies for borrow fee**: Using a Taylor expansion around [[put-call-parity]], the authors derive that the implied volatility spread (sigma_C - sigma_P) is approximately proportional to the stock borrow fee h. The formula is: sigma_C - sigma_P ≈ -sqrt(2*pi*(T-t)) * exp(d1^2/2) * h. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Strong empirical correlation**: The negated IV spread tracks the Markit indicative borrow fee very closely. For Tesla, the correlation between implied borrow fee and actual borrow fee is 0.97. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Spread-sorted portfolios lose significance after fee adjustment**: The long-short portfolio return based on IV spread drops from 0.64% per month (t=5.94) to an insignificant 0.10% (t=0.92) after adjusting for borrow fees. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Skew-sorted portfolios similarly attenuate**: IV skew-sorted long-short returns drop from 0.54% to an insignificant 0.17% after fee adjustment. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **High-fee stocks drive predictability**: Excluding stocks with borrow fees >1% per year (only 11% of the sample) reduces abnormal returns by at least two-thirds. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **17 predictors examined**: The paper systematically tests 17 options-based predictors of stock returns. All seven additional predictors derived from implied volatilities also lose significance after fee adjustment. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Not informed trading**: The results challenge the "informed trading in options" interpretation of stock return predictability from options data. The borrow fee, not private information, explains the link. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Option-implied borrow fee is extractable**: The formula h^implied ≈ -(sigma_C - sigma_P) / sqrt(2*pi*(T-t)) provides a practical way to extract borrow fees from options data. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Methodology

1. **Theoretical derivation**: Taylor expansion of [[put-call-parity]] with borrow fees to show IV spread is proportional to borrow fee.
2. **Data**: CRSP stock returns, Markit stock borrow fees (July 2006 - December 2020), OptionMetrics implied volatilities (pre-July 2024 version that assumes zero borrow fees).
3. **Portfolio sorts**: Decile portfolios sorted by IV spread, skew, and other predictors. DGTW characteristic-matched benchmarks excluding high-fee stocks.
4. **Fee adjustment**: Add cumulative borrow fees to short portfolio returns, deduct from benchmark where appropriate. Use Markit indicative fees for 2006-2020 and option-implied fees for 1996-2006 extension.
5. **Sample**: 4,933 unique stocks, ~8.4 million stock-date observations.

## Relevance to AI Trading System

- **Critical for our options flow analyst**: Any signal based on IV spread or IV skew should be interpreted as potentially reflecting [[stock-borrow-fees]] rather than informed directional views. See [[iv-spread-skew-signals]].
- **Extracting borrow fees**: The option-implied borrow fee formula gives our system a way to estimate borrow costs without expensive lending market data.
- **High-fee stock filter**: Our system should flag stocks with high implied borrow fees (extractable from IV spread) and treat any options-based signals on those stocks with extra skepticism.
- **Practical implication**: IV spread/skew strategies are not profitable after accounting for the borrow fee that a short seller would actually pay. This should temper any enthusiasm for pure IV spread signals in our trading system.

## Cross-References

- [[iv-spread-and-skew]]
- [[stock-borrow-fees]]
- [[implied-volatility]]
- [[put-call-parity]]
- [[black-scholes-model]]
- [[iv-spread-skew-signals]]
