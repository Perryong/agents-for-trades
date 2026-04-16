---
title: Retail Investor Behavior
type: concept
tags: [behavioral-finance, retail-investors, options, earnings, disposition-effect]
sources: [losing_optional.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Retail Investor Behavior

## Definition

Retail investor behavior in options markets refers to the systematic patterns, biases, and trading decisions made by non-professional individual investors ("non-professional customers" in exchange data). Understanding these patterns is valuable both for avoiding common mistakes and for identifying exploitable mispricings created by aggregate retail flow. [Source: losing_optional.pdf]

## Key Behavioral Patterns

### Attention-Driven Trading

Retail investors are drawn to trade by media coverage and salient events. High [[expected-announcement-volatility]] attracts media attention, which in turn drives retail option demand. A 1-SD increase in EAV is associated with 22% more news articles, and retail demand is concentrated among firms receiving media coverage. This is consistent with the broader behavioral finance literature on attention-based trading. [Source: losing_optional.pdf]

### Systematic Optimism / Call Bias

When retail investors trade options around earnings, they predominantly buy call options rather than puts. This is inconsistent with hedging (which would predict put buying for long stock holders) and instead reflects systematic optimism or directional speculation. [Source: losing_optional.pdf]

### Overpaying for Volatility

Retail investors systematically overpay for options relative to subsequently realized volatility. At-the-money straddles purchased before high-EAV earnings underperform by 11% relative to low-EAV straddles (t-statistic = 19.55). Retail traders pay hefty premiums for options that price in large price moves, but realized moves are insufficient to offset the premium paid. [Source: losing_optional.pdf]

### Trading in Illiquid Conditions (Wide Spreads)

Retail option trading concentrates in periods when bid-ask spreads are at their widest -- right before earnings, when market makers widen spreads to manage the unhedgeable jump risk. For high-EAV announcements, transaction costs from wide spreads add approximately 9% to retail losses. [Source: losing_optional.pdf]

### Disposition Effect in Options

After earnings announcements, retail investors are slow to close losing option positions. They continue holding options as volatility collapses post-announcement and prices decay. Straddles continue to underperform over the 2 weeks following high EAV announcements by an additional 9% (t-statistic = 8.26). This is consistent with the disposition effect documented in equities -- the tendency to hold losers and sell winners. [Source: losing_optional.pdf]

### Shift from Stocks to Options

Around earnings announcements, retail investors shift their trading activity from stocks to options. The ratio of unsigned options activity to equity activity spikes prior to earnings and drops afterward. This indicates that the forces driving retail option purchases are stronger than or distinct from those driving stock purchases. [Source: losing_optional.pdf]

## Scale and Growth

- Retail dollar option trading grew from approximately $20 billion in 2010 to approximately $240 billion in 2020, a more than tenfold increase. [Source: losing_optional.pdf]
- Retail investors lost approximately $3 billion in aggregate on options around earnings announcements during the 2010-2021 sample period. [Source: losing_optional.pdf]
- In the Netherlands, retail option investors lose an average of 1.81% per month on their option positions. [Source: losing_optional.pdf]

## Who Benefits

Market makers are the primary counterparties and beneficiaries of retail option demand around earnings. They absorb retail buying pressure by selling options, charge wide bid-ask spreads, and largely offset their positions by the announcement date. The large capital flows from retail to market makers accelerated particularly around the COVID-19 pandemic. [Source: losing_optional.pdf]

## Relevance to Our System

- Our system should specifically avoid common retail mistakes: buying options before earnings, overpaying for volatility, and holding losing positions.
- The aggregate predictability of retail behavior creates exploitable patterns for contrarian strategies (see [[fade-retail-earnings-options]]).
- High retail flow in a particular option contract should be treated as a potential contrarian indicator.
- The EAV metric provides a quantifiable way to identify when retail misbehavior is most pronounced.

## Cross-References

- [[expected-announcement-volatility]]
- [[implied-volatility]]
- [[fade-retail-earnings-options]]
- [[earnings-screener-enhancement]]
