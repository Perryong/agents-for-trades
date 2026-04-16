---
title: "TradingAgents: Multi-Agents LLM Financial Trading Framework"
type: source
tags: [multi-agent, LLM, trading-framework, debate, risk-management, backtesting]
sources: [2412.20138v7.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Citation

Xiao, Y., Sun, E., Luo, D., & Wang, W. (2025). TradingAgents: Multi-Agents LLM Financial Trading Framework. arXiv:2412.20138v7. Tauric Research, UCLA, MIT. Available at https://github.com/TauricResearch/TradingAgents.

## Summary

This is the original paper behind our codebase. TradingAgents proposes a multi-agent LLM framework that simulates a trading firm's organizational structure. It defines seven specialized agent roles organized into teams: an Analyst Team (fundamentals, sentiment, news, technical), a Researcher Team (bull/bear debaters), Trader Agents, a Risk Management Team (aggressive/neutral/conservative), and a Fund Manager. The framework uses structured communication protocols instead of raw message histories and achieves superior cumulative returns, Sharpe ratios, and maximum drawdown compared to rule-based baselines. [Source: 2412.20138v7.pdf]

## Key Findings

- **Outperforms baselines by significant margins**: TradingAgents achieved at least 23.21% cumulative return and 24.90% annual return on AAPL, GOOGL, and AMZN, surpassing the best baseline by 6.1% on three sampled stocks. [Source: 2412.20138v7.pdf]
- **Superior Sharpe Ratio**: The framework delivers the best risk-adjusted returns across all tested stocks, surpassing Buy-and-Hold, MACD, KDJ+RSI, ZMR, and SMA strategies. [Source: 2412.20138v7.pdf]
- **Controlled maximum drawdown**: Despite higher returns, MDD remained below 2, demonstrating effective risk management through the debate-based risk team. [Source: 2412.20138v7.pdf]
- **High explainability**: Unlike deep learning methods, LLM-based decisions are communicated in natural language with detailed reasoning, tool usage, and thought processes via ReAct-style prompting. [Source: 2412.20138v7.pdf]
- **Structured communication protocol**: Agents exchange structured documents and reports rather than raw conversation, reducing the "telephone effect" of information loss across agent interactions. [Source: 2412.20138v7.pdf]
- **Backbone LLM flexibility**: Uses gpt-4o-mini/gpt-4o for quick tasks and o1-preview for deep reasoning, with seamless model interchangeability. [Source: 2412.20138v7.pdf]
- **Adaptability to market conditions**: The collaborative multi-agent approach adapts to varying market conditions including high-volatility periods where traditional strategies fail. [Source: 2412.20138v7.pdf]

## Methodology

- **Backtesting period**: January 1 to March 29, 2024, across AAPL, NVDA, MSFT, META, GOOGL, and AMZN. [Source: 2412.20138v7.pdf]
- **Data sources**: Historical stock prices, news articles (Bloomberg, Yahoo, FinnHub, Reddit), social media sentiment, insider transactions, financial statements, company profiles, and 60 technical indicators. [Source: 2412.20138v7.pdf]
- **Baselines**: Buy and Hold, MACD, KDJ+RSI, ZMR, SMA. [Source: 2412.20138v7.pdf]
- **Metrics**: Cumulative Return (CR), Annualized Return (AR), Sharpe Ratio (SR), Maximum Drawdown (MDD). [Source: 2412.20138v7.pdf]
- **Agent architecture**: All agents follow the ReAct prompting framework. Communication uses structured reports with global agent state. Bull/bear researchers debate for n rounds with a facilitator selecting the prevailing perspective. Risk management team deliberates from three risk profiles. [Source: 2412.20138v7.pdf]

## Relevance to AI Trading System

This is the foundational paper for our agents-for-trades application. Our implementation directly mirrors the described architecture with analyst agents, researcher debate, trader, risk management team, and fund manager. See [[tradingagents-paper-alignment]] for a detailed audit of how our implementation aligns with and diverges from the paper. The [[learning-externality]] findings from Paper 7 suggest caution about scaling multiple instances.

## Cross-References

- [[tradingagents-framework]] — entity page for the framework
- [[multi-agent-llm-trading]] — the paradigm this paper defines
- [[multi-agent-analysis-pipeline]] — the analysis strategy extracted from this paper
- [[tradingagents-paper-alignment]] — alignment audit of our implementation
