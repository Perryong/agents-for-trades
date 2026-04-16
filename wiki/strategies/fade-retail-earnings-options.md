---
title: Fade Retail Earnings Options Strategy
type: strategy
tags: [options, earnings, retail-investors, volatility-selling, contrarian]
sources: [losing_optional.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Fade Retail Earnings Options Strategy

## Overview

A contrarian strategy that exploits the systematic tendency of [[retail-investor-behavior]] to overpay for options before high [[expected-announcement-volatility]] earnings announcements. The strategy involves selling option premium (or positioning as a volatility seller) ahead of these events, effectively taking the other side of retail demand. Based on findings from de Silva, So & Smith (2026). [Source: losing_optional.pdf]

## Setup Conditions

1. **Identify upcoming earnings announcements** with high [[expected-announcement-volatility]] (EAV).
2. **Compute AbnormalIV**: AbnormalIV = (IV_30 - IV_60) / (1/30 - 1/60) using options data. Alternatively, use MAX_EA (largest absolute return over 5 years of EAs) as a simpler proxy.
3. **Target the top quintile of EAV**: Retail overpaying is most pronounced for high-EAV announcements, where losses average 10-14%. [Source: losing_optional.pdf]
4. **Confirm media coverage**: The mechanism is attention-driven. High EAV + media coverage is the strongest predictor of retail option demand. Check for elevated news article counts in the days before earnings. [Source: losing_optional.pdf]

## Entry Rules

### Primary Approach: Sell ATM Straddles

- **Sell an ATM straddle** (short ATM call + short ATM put) on the underlying stock 2-5 days before the earnings announcement.
- Use options expiring 10+ days after the announcement to match the retail holding pattern.
- Rationale: Retail investors buy ATM calls disproportionately; straddle returns underperform by 11% on high-EAV dates vs. low-EAV dates. [Source: losing_optional.pdf]

### Alternative Approach: Sell Calls

- **Sell ATM or slightly OTM calls** if directional neutral/bearish, since retail demand concentrates in calls (not puts). [Source: losing_optional.pdf]

### Timing

- Enter 3-5 days before the earnings announcement (t=-5 to t=-3), when retail buying is ramping but before the peak.
- Retail buying accelerates most from t=-5 to t=-2 relative to the announcement date. [Source: losing_optional.pdf]

## Exit Rules

- **Close immediately after earnings** (t=0 or t=1) to capture the volatility crush.
- Do NOT hold through the full post-announcement period as additional edge from retail holding exists but adds unnecessary risk.
- Alternative: hold for 2 weeks post-announcement to capture the additional 9% straddle underperformance from retail's slow closing of positions. [Source: losing_optional.pdf]

## Position Sizing

- Size based on the maximum loss from the short straddle (theoretically unlimited for calls, limited to strike minus premium for puts).
- Conservative sizing: risk no more than 1-2% of portfolio per earnings event.
- Consider portfolio-level diversification across multiple earnings events in the same cycle.

## Risk Management

- **Tail risk**: Individual earnings announcements can produce extreme moves that exceed the premium collected. A single large miss/beat can wipe out many successful trades.
- **Use defined-risk alternatives**: Iron condors or iron butterflies cap maximum loss.
- **Avoid single-name concentration**: Spread across many earnings events to diversify idiosyncratic risk.
- **Monitor implied variance**: If AbnormalIV is extremely high, the market may be correctly pricing a genuinely uncertain event. The edge comes from the average case, not every individual event.
- **Liquidity**: Only trade names with liquid options and reasonable bid-ask spreads. The strategy depends on capturing retail's overpayment; if spreads are too wide, the edge goes to market makers instead.

## Historical Evidence

- Retail investors lose 5-9% on average across all earnings trades, and 10-14% on high-EAV trades. [Source: losing_optional.pdf]
- ATM straddles underperform by 11% on high-EAV dates relative to low-EAV dates (t-statistic = 19.55). [Source: losing_optional.pdf]
- Straddles continue to underperform for 2 weeks post-announcement by an additional 9% (t-statistic = 8.26). [Source: losing_optional.pdf]
- Market makers -- the professional counterparties to retail -- are the primary beneficiaries, suggesting the edge is real and persistent. [Source: losing_optional.pdf]
- Aggregate retail losses: ~$3 billion over the 2010-2021 sample period. [Source: losing_optional.pdf]

## Caveats

- **This is not risk-free income**: Short option strategies have fat-tailed risk. The average profitability comes from the statistical tendency, not from guaranteed outcomes on each trade.
- **Market maker advantage**: Market makers benefit from bid-ask spread income, inventory management, and hedging capabilities that retail traders (and our system) may not have.
- **Regulatory environment**: The SEC and exchanges are actively scrutinizing retail option trading. The regulatory landscape may change.
- **Changing retail behavior**: As retail traders become more sophisticated, the edge may diminish over time.

## Cross-References

- [[expected-announcement-volatility]]
- [[retail-investor-behavior]]
- [[implied-volatility]]
- [[earnings-screener-enhancement]]
