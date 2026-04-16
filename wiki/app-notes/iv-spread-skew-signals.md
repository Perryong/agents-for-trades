---
title: "App Note: IV Spread/Skew Signals for Options Flow Analyst"
type: app-note
tags: [options-flow, iv-spread, iv-skew, borrow-fees, signal-interpretation]
sources: [1-s2.0-S0304405X25001618-main.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# IV Spread/Skew Signals for Options Flow Analyst

## What to Change

Reinterpret how our options flow analyst uses [[iv-spread-and-skew]] signals. Currently, a large negative IV spread (put IV >> call IV) might be interpreted as bearish informed trading. Based on Muravyev, Pearson & Pollet (2025), this signal should instead be treated primarily as a [[stock-borrow-fees]] indicator, with the following specific changes:

1. **Add a borrow fee filter**: Before treating IV spread/skew as a directional signal, estimate the implied borrow fee and determine if the stock is "high-fee" (>1% annual). If so, discount the signal heavily.
2. **Extract implied borrow fees**: Compute h^implied from the IV spread and use it as a standalone feature for risk assessment.
3. **Flag hard-to-borrow stocks**: When implied borrow fee is elevated, warn that short-biased strategies on this stock face additional friction.

## Why (with Source Citation)

Muravyev, Pearson & Pollet (2025) provide definitive evidence that:

- The IV spread is **proportional to the stock borrow fee**: sigma_C - sigma_P ≈ -sqrt(2*pi*(T-t)) * exp(d1^2/2) * h. For Tesla, the correlation between option-implied borrow fee and actual Markit borrow fee is 0.97. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Predictive power disappears after fee adjustment**: IV spread-sorted long-short portfolio returns drop from 0.64%/month (t=5.94) to an insignificant 0.10%/month (t=0.92) after adjusting for borrow fees. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **High-fee stocks drive all the action**: Excluding the 11% of stocks with borrow fees >1%/year eliminates at least two-thirds of the apparent predictability. Decile 1 (lowest spread / most "bearish" signal) has 83.5 high-fee stocks on average with 6.86% average annual fee. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **All 17 options-based predictors attenuate**: Not just the spread and skew, but all options-based stock return predictors examined (IV changes, vol-of-vol, variance asymmetry, etc.) lose significance after fee adjustment. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Not informed trading**: The traditional "informed traders prefer options" explanation is not supported. The borrow fee, not private information, explains why options data predicts stock returns. [Source: 1-s2.0-S0304405X25001618-main.pdf]

## Expected Impact

- **Fewer false positives**: Our options flow analyst will stop generating bearish signals on stocks that simply have high borrow fees, reducing noise in our recommendations.
- **Better risk assessment**: Knowing the implied borrow fee helps our risk manager assess the true cost of short positions and options strategies.
- **New feature: borrow fee estimation**: Provides free access to borrow cost estimates from options data, without requiring expensive lending market subscriptions (Markit, etc.).
- **More accurate signal interpretation**: Remaining IV spread signal (after borrow fee adjustment) may still contain residual information, but it is small and likely not exploitable after transaction costs.

## Implementation Notes

### Implied Borrow Fee Computation

For ATM options (where exp(-d1^2/2) ≈ 1):

h^implied ≈ -(sigma_C - sigma_P) / sqrt(2*pi*(T-t))

**Practical steps**:
1. Pull 30-day ATM call and put implied volatilities.
2. Compute IV spread = sigma_C - sigma_P.
3. Compute h^implied = -IV_spread / sqrt(2 * pi * (30/365)).

### Where to Integrate

- **Options flow analyst** agent: Add borrow fee estimation as a preprocessing step before interpreting IV spread/skew signals.
- **Risk manager** agent: Receive implied borrow fee as an input; flag stocks where borrow costs may significantly impact strategy returns.
- **Screener**: Add an "implied borrow fee" column to help filter out high-cost-to-short stocks.

### Signal Reinterpretation Logic

```
if implied_borrow_fee > 1%:
    # High-fee stock: IV spread signal is mostly borrow fee, not informed trading
    discount_iv_spread_signal(weight=0.1)  # heavily discount
    flag_short_selling_risk(borrow_fee=implied_borrow_fee)
elif implied_borrow_fee > 0.5%:
    # Moderate fee: partially discount signal
    discount_iv_spread_signal(weight=0.5)
else:
    # Low fee: IV spread may contain genuine information
    # but even here, after-fee returns are marginal
    use_iv_spread_signal(weight=0.8)
```

### Additional Options-Based Predictors to Discount

Per Table 9 in the paper, these additional predictors also lose significance after fee adjustment and should be similarly discounted for high-fee stocks:
- IV change (call, put, call/put)
- Volatility-of-volatility
- Variance asymmetry
- Ex-ante skewness
- IV slope (down 30)
- O/S ratio
- Option bid-ask spread

[Source: 1-s2.0-S0304405X25001618-main.pdf]

### What Survives Fee Adjustment

Two categories of predictors show some resilience to fee adjustment:
- **Risk premium measures** (Martin-Wagner bound, Chabi-Yo-Dim-Vilkov bound): These are theoretically grounded in expected returns, not the borrow fee, and show some predictive power after adjustment. [Source: 1-s2.0-S0304405X25001618-main.pdf]
- **Implied-realized volatility difference** (IV - RV): Sorting on this yields fee-adjusted abnormal returns of -0.65% on decile 1 and +1.41% on the long-short portfolio. This predictor primarily reflects the volatility risk premium rather than borrow fees. [Source: 1-s2.0-S0304405X25001618-main.pdf]

These surviving predictors could be prioritized in our options flow analyst.

## Cross-References

- [[iv-spread-and-skew]]
- [[stock-borrow-fees]]
- [[implied-volatility]]
- [[put-call-parity]]
