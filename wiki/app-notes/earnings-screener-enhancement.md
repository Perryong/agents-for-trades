---
title: "App Note: Earnings Screener Enhancement with EAV"
type: app-note
tags: [screener, earnings, EAV, retail-investors, volatility]
sources: [losing_optional.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Earnings Screener Enhancement with EAV

## What to Change

Enhance our earnings screener to compute and display [[expected-announcement-volatility]] (EAV) metrics for upcoming earnings announcements, flagging high-EAV events where [[retail-investor-behavior]] creates the most significant mispricings.

## Why (with Source Citation)

de Silva, So & Smith (2026) provide compelling evidence that:

- Retail investors **systematically lose 10-14%** on options around high-EAV earnings announcements, compared to 5-9% on average across all earnings. The edge is concentrated in the high-EAV subsample. [Source: losing_optional.pdf]
- **EAV is measurable in advance**: The AbnormalIV metric can be computed 5+ days before earnings from publicly available options data. [Source: losing_optional.pdf]
- **Media coverage amplifies the pattern**: High-EAV events generate 22% more news articles, which attract retail attention and drive option demand. Checking for media coverage further refines the signal. [Source: losing_optional.pdf]
- **Market makers profit consistently**: The pattern is not noise -- professional counterparties (market makers) have been consistently profiting from the other side of retail flow around earnings for over a decade, with retail losses totaling ~$3 billion from 2010-2021. [Source: losing_optional.pdf]

## Expected Impact

- **Identify highest-edge earnings events**: The screener would surface the top quintile of EAV announcements where the contrarian [[fade-retail-earnings-options]] strategy has the strongest expected performance.
- **Improve trade selection**: Rather than treating all earnings as equal-opportunity events, the system can prioritize high-EAV events for premium selling.
- **Risk awareness**: The system can also warn against buying options before high-EAV earnings -- a common retail mistake our system should avoid.

## Implementation Notes

### AbnormalIV Computation

The primary metric is:

AbnormalIV_t = (IV_{t,30} - IV_{t,60}) / (1/30 - 1/60)

where IV_{t,tau} is the Black-Scholes implied variance for an option with tau days to maturity.

**Practical implementation**:
1. For each upcoming earnings announcement, pull 30-day and 60-day ATM implied volatilities from options data (e.g., via CBOE, OptionMetrics, or derived from yfinance option chains).
2. Compute AbnormalIV as above.
3. Rank all upcoming earnings by AbnormalIV.
4. Flag the top quintile as "high-EAV" events.

### MAX_EA Alternative

If real-time IV data is unavailable, use MAX_EA as a simpler proxy:

MAX_EA = max(|return_i|) for i in {last 20 quarterly earnings announcements}

This captures the historical propensity for large moves and is fully computable from historical price data. [Source: losing_optional.pdf]

### Where to Integrate

- **Screener routes** (`api/screener_routes.py`): Add an EAV computation endpoint that enriches earnings calendar data with AbnormalIV scores.
- **Screener agent** (`tradingagents/agents/screener/`): Have the screener agent include EAV analysis in its output.
- **Frontend** (`frontend/src/hooks/useScreener.ts`): Display EAV scores in the screener UI, with color coding for high-EAV events.

### Suggested Data Flow

1. Fetch upcoming earnings dates (already available from our data sources).
2. For each ticker with upcoming earnings:
   a. Pull current options chain.
   b. Find ATM options at ~30-day and ~60-day expirations.
   c. Compute AbnormalIV.
   d. Compute MAX_EA from historical earnings returns.
3. Sort by AbnormalIV descending.
4. Display in screener with:
   - EAV score (AbnormalIV value)
   - EAV rank (quintile)
   - MAX_EA (historical max move)
   - Media coverage indicator (optional: news article count)
   - Recommended action: "Consider selling premium" for high-EAV, "Neutral" for low-EAV.

### Additional Enrichments

- **Retail flow indicator**: If we can estimate retail option buying (e.g., from unusual small-lot activity), combine with EAV for a stronger signal.
- **IV term structure visualization**: Show the 30-day vs 60-day IV to make the EAV intuition visual.
- **Historical EAV performance**: For each ticker, show how past high-EAV vs low-EAV earnings resolved (realized move vs implied move).

## Cross-References

- [[expected-announcement-volatility]]
- [[retail-investor-behavior]]
- [[fade-retail-earnings-options]]
- [[implied-volatility]]
