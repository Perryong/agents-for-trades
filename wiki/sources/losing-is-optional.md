---
title: "Losing is Optional: Retail Option Trading and Expected Announcement Volatility"
type: source
tags: [retail-investors, options, earnings, volatility, behavioral-finance, market-makers]
sources: [losing_optional.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Losing is Optional: Retail Option Trading and Expected Announcement Volatility

## Citation

de Silva, T., So, E.C. & Smith, K. (2026). Losing is Optional: Retail Option Trading and Expected Announcement Volatility. *Review of Finance*, 30, 489-535. doi:10.1093/rof/rfaf052. Stanford University / MIT Sloan.

## Abstract Summary

This paper documents how [[retail-investor-behavior]] in options markets is driven by [[expected-announcement-volatility]] (EAV) around earnings announcements. Retail investors systematically buy options before high-EAV earnings announcements, overpay for volatility relative to realized outcomes, trade in options with enormous bid-ask spreads, and then fail to close losing positions post-announcement. The result is average losses of 5-9% on all earnings trades and 10-14% on high-EAV trades. Market makers are the primary counterparties and beneficiaries. [Source: losing_optional.pdf]

## Key Findings

- **Retail option demand driven by EAV**: Retail investors concentrate option purchases in the days immediately preceding earnings announcements, with demand increasing monotonically with [[expected-announcement-volatility]]. A 1-SD increase in AbnormalIV translates into roughly 2,300 more options bought. [Source: losing_optional.pdf]
- **Retail overpays for volatility**: Options straddles underperform on high-EAV announcement dates by a whopping 11% relative to low-EAV dates (t-statistic = 19.55). Retail investors systematically overpay for options relative to realized volatility. [Source: losing_optional.pdf]
- **Three factors destroy retail wealth**: (1) Overpaying for volatility relative to realized outcomes, (2) trading options with enormous bid-ask spreads (adding ~9% in costs for high-EAV announcements), and (3) holding losing positions post-announcement as prices decay (disposition effect). [Source: losing_optional.pdf]
- **Aggregate losses ~$3 billion**: Over the sample window (2010-2021), retail investors lost approximately $3 billion on options around earnings announcements. [Source: losing_optional.pdf]
- **Market makers profit**: Market makers are the primary absorbers of retail order flow around earnings, taking the opposite side of retail positions. Market makers largely offset their positions by earnings day. [Source: losing_optional.pdf]
- **Media attention is the mechanism**: High EAV attracts media coverage, which grabs retail attention and generates systematic optimism, leading to long positions in both stocks and options. The link between EAV and retail demand is concentrated among firms with media coverage. [Source: losing_optional.pdf]
- **Not skewness-seeking or hedging**: Retail purchases concentrate in ATM calls (not OTM lottery tickets), and they buy calls rather than protective puts, ruling out hedging and skewness-preference explanations. [Source: losing_optional.pdf]
- **Retail trading has grown >10x**: Retail dollar option trading grew from ~$20B in 2010 to ~$240B in 2020, making this pattern increasingly significant. [Source: losing_optional.pdf]

## Methodology

1. **Data**: Nasdaq Options Trade Outline (NOTO) and PHLX Options Trade Outline (PHOTO) end-of-day files providing contract-day level buying/selling by five clientele groups (retail, professional, market maker, broker/dealer, firm). Sample: 2010-2021.
2. **EAV measurement**: AbnormalIV = (IV_30 - IV_60) / (1/30 - 1/60), using Black-Scholes implied variance from OptionMetrics. Also use MAX_EA (largest absolute return over recent 5 years of EAs) as a proxy.
3. **Straddle returns**: At-the-money straddle returns around earnings to isolate volatility pricing from directional bets.
4. **Position tracking**: Cumulative delta-adjusted trader positions by clientele group in event time relative to earnings announcements.
5. **Sample**: 32,758 quarterly earnings announcements spanning 2010-2021.

## Relevance to AI Trading System

- Provides strong evidence for a contrarian strategy: fading retail earnings options demand (see [[fade-retail-earnings-options]]).
- The EAV metric (AbnormalIV) could be computed by our earnings screener to identify high-EAV announcements where retail overpaying is most severe.
- Supports the principle that our system should avoid buying options before earnings (a retail mistake) and instead consider selling premium.
- The finding that retail demand drives up option-implied variances by 40% in the top quintile suggests significant IV inflation that could be exploited.

## Cross-References

- [[expected-announcement-volatility]]
- [[retail-investor-behavior]]
- [[implied-volatility]]
- [[fade-retail-earnings-options]]
- [[earnings-screener-enhancement]]
