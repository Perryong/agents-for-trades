---
title: TradingAgents Framework
type: entity
tags: [framework, multi-agent, LLM, trading, Tauric-Research]
sources: [2412.20138v7.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Description

TradingAgents is a multi-agent LLM financial trading framework developed by Tauric Research (UCLA/MIT) that simulates a real-world trading firm's organizational structure using specialized LLM agents. It is the foundational framework behind our agents-for-trades application. The open-source implementation is available at https://github.com/TauricResearch/TradingAgents. [Source: 2412.20138v7.pdf]

## Architecture

The framework defines seven agent roles organized into five teams:

### Analyst Team (concurrent)
| Agent | Data Domain | Tools |
|-------|------------|-------|
| Fundamentals Analyst | Financial statements, earnings, insider transactions | Company profile APIs, financial data |
| Sentiment Analyst | Social media, sentiment scores | Web search, Reddit/X APIs, sentiment models |
| News Analyst | News articles, macro indicators | Bloomberg, FinnHub, Reuters APIs |
| Technical Analyst | Price patterns, volume, indicators | Code execution, 60 technical indicators |

### Researcher Team (debate)
- **Bullish Researcher**: Advocates for investment, highlights growth and positive indicators
- **Bearish Researcher**: Highlights risks, downsides, unfavorable signals
- **Debate Facilitator**: Moderates n rounds of debate, selects prevailing perspective

### Trader Agent
Synthesizes analyst reports and debate outcomes into buy/sell/hold decisions with reasoning.

### Risk Management Team (deliberation)
- **Aggressive**: High-reward, high-risk perspective
- **Neutral**: Balanced perspective
- **Conservative**: Risk mitigation emphasis
They engage in n rounds of natural language discussion guided by a facilitator.

### Fund Manager
Reviews risk management output, makes final approval, updates agent state.

[Source: 2412.20138v7.pdf]

## Communication Protocol

Agents exchange structured documents and reports rather than raw conversation. Each role extracts or queries necessary details from the global agent state, processes them, and returns a completed report. Natural language dialogue is reserved for agent-to-agent debates (researcher and risk management teams). [Source: 2412.20138v7.pdf]

## Backbone LLMs

- **Quick-thinking** (gpt-4o-mini, gpt-4o): Data retrieval, summarization, tabular data conversion
- **Deep-thinking** (o1-preview): Decision-making, evidence-based report writing, debate
- GPU-free deployment, API-only, with seamless model interchangeability

[Source: 2412.20138v7.pdf]

## Performance

Backtested January-March 2024 on AAPL, GOOGL, AMZN:
- Cumulative Return: 23-27% (6-25% improvement over best baseline)
- Sharpe Ratio: 5.60-8.21 (best across all baselines)
- Maximum Drawdown: < 2 (competitive with risk-focused baselines)

[Source: 2412.20138v7.pdf]

## Connections

- **Authors**: Yijia Xiao, Edward Sun, Di Luo, Wei Wang (UCLA, MIT, Tauric Research)
- **Related frameworks**: MetaGPT (structured communication inspiration), TradingGPT, FinAgent
- **Our implementation**: agents-for-trades app, which extends this framework with a screener, options analysis, and a web UI

## Cross-References

- [[multi-agent-llm-trading]] — the paradigm this framework embodies
- [[multi-agent-analysis-pipeline]] — the analysis strategy it implements
- [[tradingagents-paper-alignment]] — audit of our implementation vs. the paper
