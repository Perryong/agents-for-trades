---
title: Wiki Index
type: overview
tags: [index]
sources: []
created: 2026-04-16
updated: 2026-04-16
---

# Trading Knowledge Wiki — Index

## Sources

| Page | Summary |
|------|---------|
| [losing-is-optional](sources/losing-is-optional.md) | Bauer et al. (2024) — Retail option trading around earnings, expected announcement volatility |
| [options-market-information-stock-returns](sources/options-market-information-stock-returns.md) | Ge & Lin (2025) — Why options market information predicts stock returns (IV spread, skew, borrow fees) |
| [volatility-pairs-trading](sources/volatility-pairs-trading.md) | Clements & Todorova (2025) — Options pairs trading strategies using volatility |
| [autonomous-ai-option-hedging](sources/autonomous-ai-option-hedging.md) | Hu et al. (2025) — RLOP and Adaptive-QLBS for shortfall-aware RL options hedging |
| [tradingagents-multi-agent-llm-framework](sources/tradingagents-multi-agent-llm-framework.md) | Xiao et al. (2025) — The original TradingAgents paper behind our codebase |
| [ai-powered-trading-algorithmic-collusion](sources/ai-powered-trading-algorithmic-collusion.md) | Dou, Goldstein & Ji (2025) — RL agents develop collusive behavior via price-trigger and over-pruning mechanisms |
| [deep-learning-to-trade](sources/deep-learning-to-trade.md) | Gufler, Sangiorgi & Tarantino (2025) — Negative learning externality when multiple DRL agents trade |

## Concepts

| Page | Summary |
|------|---------|
| [algorithmic-collusion](concepts/algorithmic-collusion.md) | When AI traders autonomously develop collusive behavior |
| [delta-hedging](concepts/delta-hedging.md) | Traditional delta hedging and its limitations under frictions |
| [expected-announcement-volatility](concepts/expected-announcement-volatility.md) | Volatility priced into options around earnings announcements |
| [implied-volatility](concepts/implied-volatility.md) | Market's expectation of future volatility embedded in option prices |
| [iv-spread-and-skew](concepts/iv-spread-and-skew.md) | IV spread and skew as predictive signals for stock returns |
| [learning-externality](concepts/learning-externality.md) | How multiple AI agents degrade each other's learning through noise injection |
| [market-efficiency](concepts/market-efficiency.md) | EMH and how AI trading affects price efficiency (both positively and negatively) |
| [microstructure-effects](concepts/microstructure-effects.md) | Market microstructure effects on options and stock prices |
| [multi-agent-llm-trading](concepts/multi-agent-llm-trading.md) | Paradigm of using multiple specialized LLM agents for trading decisions |
| [reinforcement-learning-hedging](concepts/reinforcement-learning-hedging.md) | RL approaches to options hedging: QLBS, RLOP, Deep Hedging |
| [retail-investor-behavior](concepts/retail-investor-behavior.md) | Retail investor behavioral patterns in options trading |
| [shortfall-probability](concepts/shortfall-probability.md) | Shortfall-aware risk measure separating loss frequency from severity |
| [stock-borrow-fees](concepts/stock-borrow-fees.md) | Short-selling costs and their reflection in options prices |
| [volatility-pairs-trading](concepts/volatility-pairs-trading.md) | Trading volatility mean-reversion across correlated assets |

## Entities

| Page | Summary |
|------|---------|
| [black-scholes-model](entities/black-scholes-model.md) | The foundational options pricing model |
| [deep-hedging](entities/deep-hedging.md) | Buehler et al.'s neural network hedging approach |
| [put-call-parity](entities/put-call-parity.md) | Fundamental relationship between put and call option prices |
| [qlbs-model](entities/qlbs-model.md) | Q-Learner in Black-Scholes — backward value-based RL hedging |
| [rlop-model](entities/rlop-model.md) | Replication Learning of Option Pricing — forward shortfall-aware RL hedging |
| [tradingagents-framework](entities/tradingagents-framework.md) | The multi-agent LLM trading framework our app is built on |

## Strategies

| Page | Summary |
|------|---------|
| [fade-retail-earnings-options](strategies/fade-retail-earnings-options.md) | Fade retail earnings options mispricing strategy |
| [multi-agent-analysis-pipeline](strategies/multi-agent-analysis-pipeline.md) | The TradingAgents 5-stage analysis-to-execution pipeline |
| [options-pairs-trading-strategy](strategies/options-pairs-trading-strategy.md) | Options pairs trading using volatility mean-reversion |
| [rl-options-hedging](strategies/rl-options-hedging.md) | Practical RL hedging strategy using RLOP/QLBS for short call positions |

## App Notes

| Page | Summary |
|------|---------|
| [collusion-awareness](app-notes/collusion-awareness.md) | Regulatory considerations from algorithmic collusion research |
| [earnings-screener-enhancement](app-notes/earnings-screener-enhancement.md) | Enhance screener with earnings-related volatility signals |
| [improve-volatility-analyst](app-notes/improve-volatility-analyst.md) | Improve the volatility analyst agent |
| [iv-spread-skew-signals](app-notes/iv-spread-skew-signals.md) | Use IV spread and skew as predictive signals |
| [learning-externality-mitigation](app-notes/learning-externality-mitigation.md) | How learning externality findings inform our multi-agent design |
| [rl-hedging-for-greeks-monitor](app-notes/rl-hedging-for-greeks-monitor.md) | How RLOP/QLBS could enhance our Greeks monitor agent |
| [tradingagents-paper-alignment](app-notes/tradingagents-paper-alignment.md) | Audit of our implementation vs. the original paper |

## Comparisons

(None yet)
