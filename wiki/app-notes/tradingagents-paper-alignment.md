---
title: TradingAgents Paper Alignment Audit
type: app-note
tags: [app-note, tradingagents, alignment, architecture, audit]
sources: [2412.20138v7.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## What to Change

Audit and document how our agents-for-trades implementation aligns with and diverges from the original TradingAgents paper (Xiao et al., 2025) to identify gaps and potential improvements.

## Why (Source Citation)

Our application is built on the [[tradingagents-framework]] described in the paper. Understanding alignment ensures we benefit from the paper's validated design decisions and that our divergences are intentional improvements rather than accidental omissions. [Source: 2412.20138v7.pdf]

## Alignment Analysis

### Implemented as Described

| Paper Component | Our Implementation | Status |
|----------------|-------------------|--------|
| Fundamentals Analyst | `fundamentals_analyst.py` | Aligned |
| News Analyst | `news_analyst.py` | Aligned |
| Social Media/Sentiment Analyst | `social_media_analyst.py` | Aligned |
| Technical Analyst | `technical_analyst.py` | Aligned |
| Market Analyst | `market_analyst.py` | Extended (not in paper) |
| Risk Manager | `risk_manager.py` | Aligned with extensions |
| Screener Agent | `screener_agent.py` | Extended (not in paper) |
| Agent state management | `agent_states.py` | Aligned |
| Graph-based propagation | `propagation.py`, `setup.py` | Aligned |

### Key Divergences

**1. Market Analyst (Addition)**
Our system adds a dedicated market analyst agent not present in the paper. This extends the analyst team from four to five specialists. [Source: 2412.20138v7.pdf]

**2. Screener Agent (Addition)**
Our system includes a stock screener agent for pre-filtering candidates, which is not part of the paper's architecture. This is a practical extension for the web UI workflow. [Source: 2412.20138v7.pdf]

**3. Risk Manager Extensions**
Our risk manager has been extended with strategy context and stop-loss enforcement (per recent development phases), going beyond the paper's three-perspective deliberation model. [Source: 2412.20138v7.pdf]

**4. Web UI and API Layer**
The paper describes a CLI/programmatic framework. Our implementation adds a full web frontend with API routes, chart screens, and interactive components. This is an application-layer extension.

**5. Bull/Bear Researcher Team**
The paper describes explicit bullish and bearish researcher agents with a facilitator. Our implementation's debate mechanism should be audited to verify it faithfully implements n-round debate with facilitator selection. [Source: 2412.20138v7.pdf]

**6. Risk Management Team Structure**
The paper specifies three risk perspectives (aggressive/neutral/conservative) engaging in n rounds of discussion. Our implementation should verify this three-perspective deliberation is intact. [Source: 2412.20138v7.pdf]

**7. Backbone LLM Strategy**
The paper uses gpt-4o-mini for quick tasks and o1-preview for deep reasoning. Our implementation may use different model assignments. Alignment should be verified. [Source: 2412.20138v7.pdf]

### Gaps to Investigate

1. **Communication protocol fidelity**: Does our implementation use structured documents and reports as described, or has it drifted toward raw message passing? [Source: 2412.20138v7.pdf]
2. **ReAct prompting**: Are all agents using the ReAct framework as specified? [Source: 2412.20138v7.pdf]
3. **Fund Manager role**: Is the final approval authority implemented as a distinct agent, or merged with another role? [Source: 2412.20138v7.pdf]
4. **Data source coverage**: The paper specifies Bloomberg, Yahoo, FinnHub, Reddit, SEDI, EODHD. Verify which sources are active in our implementation. [Source: 2412.20138v7.pdf]

## Expected Impact

- Identify missing features that could improve performance (if the paper's design was validated for a reason)
- Confirm that our extensions are compatible with the validated architecture
- Guide future development priorities based on gap significance

## Implementation Notes

This audit should be updated periodically as the codebase evolves. Each gap should be evaluated for whether it represents:
- A deliberate improvement (keep)
- A practical simplification (evaluate trade-off)
- An accidental omission (prioritize fixing)

## Cross-References

- [[tradingagents-framework]] — the framework entity page
- [[multi-agent-llm-trading]] — the paradigm
- [[multi-agent-analysis-pipeline]] — the strategy we implement
- [[learning-externality-mitigation]] — performance considerations
