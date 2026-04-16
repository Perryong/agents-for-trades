---
title: Expected Announcement Volatility
type: concept
tags: [earnings, volatility, options, retail-investors, implied-volatility]
sources: [losing_optional.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Expected Announcement Volatility (EAV)

## Definition

Expected Announcement Volatility (EAV) is a measure of how much the market expects a stock's price to move around an earnings announcement. It is derived from the options market by comparing short-term and long-term [[implied-volatility]], exploiting the fact that earnings-related uncertainty is concentrated in short-dated options. [Source: losing_optional.pdf]

## How It Works

### AbnormalIV Metric

The primary EAV measure used in the literature is AbnormalIV:

AbnormalIV_t = (IV_{t,30} - IV_{t,60}) / (1/30 - 1/60)

where IV_{t,tau} is the Black-Scholes implied variance from OptionMetrics for an option with tau days to maturity at time t (measured in event-time relative to the earnings announcement). [Source: losing_optional.pdf]

### Intuition

When investors expect a large price move at earnings:
- Short-term (30-day) implied variance rises because the expected jump constitutes a larger proportion of the short-term option's remaining lifetime.
- Long-term (60-day) implied variance rises less because the same jump is a smaller fraction of the option's life.
- The difference isolates the earnings-specific component of implied volatility.

Formally, if stock prices follow a log-normal diffusion with jumps at earnings, AbnormalIV at t=0 measures precisely the expected squared jump on the EA date under the risk-neutral measure. [Source: losing_optional.pdf]

### MAX_EA Alternative Proxy

An alternative proxy for EAV is MAX_EA: the firm's largest absolute return over its most recent 5 years of quarterly earnings announcements. This is based on the idea that investors and media use extreme historical outcomes to forecast future announcement volatility. [Source: losing_optional.pdf]

## Empirical Evidence

- Retail option purchases increase monotonically across quintiles of AbnormalIV. In the top quintile, retail investors are the only clientele group with statistically significant net long positions prior to announcements. [Source: losing_optional.pdf]
- For announcements in the top quintile of retail option purchases, option-implied variances escalate by 40% more in the days immediately prior. [Source: losing_optional.pdf]
- High EAV spurs media coverage: a 1-SD increase in AbnormalIV coincides with a 22% increase in news articles published pre-announcement. Media coverage is the attention mechanism that attracts retail traders. [Source: losing_optional.pdf]
- The relationship between EAV and retail demand has strengthened over time, peaking around the COVID-19 pandemic and the secular rise in retail option participation. [Source: losing_optional.pdf]

## Relevance to Our System

- AbnormalIV is a computable signal from OptionMetrics (or equivalent options data) that our earnings screener could use to identify high-EAV events.
- High-EAV announcements are precisely where [[retail-investor-behavior]] creates the largest mispricings (overpaying for options), making them attractive for contrarian strategies.
- Our system should flag high-EAV earnings as opportunities for the [[fade-retail-earnings-options]] strategy.
- See [[earnings-screener-enhancement]] for implementation details.

## Cross-References

- [[implied-volatility]]
- [[retail-investor-behavior]]
- [[fade-retail-earnings-options]]
- [[earnings-screener-enhancement]]
