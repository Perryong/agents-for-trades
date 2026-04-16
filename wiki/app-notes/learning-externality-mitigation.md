---
title: Learning Externality Mitigation
type: app-note
tags: [app-note, multi-agent, learning-externality, backtesting, market-impact]
sources: [Sangiorgi_Deep__Learning_to_Trade.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## What to Change

Incorporate awareness of the [[learning-externality]] into our system's backtesting methodology, performance expectations, and multi-agent architecture design.

## Why (Source Citation)

Gufler, Sangiorgi & Tarantino (2025) demonstrate that when multiple DRL trading agents interact in a market with endogenous prices:

- Each agent's exploratory trades inject noise into the price process, diluting learning signals for all others. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Quantitative performance degrades as the number of AI traders or collective wealth share grows. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Return predictability remains elevated and liquidity is lower than the rational benchmark. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- **Critically: partial-equilibrium backtests on fixed historical data overstate both AI strategy profitability and positive market impact.** [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

This directly affects our [[tradingagents-framework]]:
- Our backtests use historical data where the system's trades do not affect prices
- If our system and similar systems proliferate, collective performance will be worse than individual backtests suggest
- Our multi-agent architecture (multiple analysts reading the same market) is a microcosm of the multi-agent learning problem

## Expected Impact

- **Realistic performance expectations**: Users understand that live performance will likely underperform backtests
- **Robust architecture**: Design choices that reduce our system's vulnerability to signal degradation from AI-crowded markets
- **Better backtesting**: Move toward equilibrium-aware evaluation over time

## Implementation Notes

### Backtesting Methodology Improvements
1. **Discount backtest results**: Apply a systematic performance haircut to backtest results shown to users. The paper suggests qualitative alignment but quantitative shortfall when multiple agents interact. A conservative 15-30% discount on expected returns would be prudent.
2. **Slippage and impact modeling**: Even without full equilibrium modeling, add realistic slippage estimates that account for the possibility that other AI systems are trading the same signals
3. **Regime-conditional reporting**: Report backtest results separately for calm and stress regimes, noting that the learning externality is more severe when more agents are active (calm periods with high AI adoption)

### Architecture Design
1. **Signal diversity within our system**: Our four-analyst design already provides diversity, but ensure analysts are not over-correlated. If all four analysts converge on the same signal, the system effectively becomes a single-agent system.
2. **Contrarian signal weighting**: Consider giving extra weight to the bearish researcher when all analysts agree, as unanimous agreement may indicate a crowded trade
3. **Stale signal detection**: Monitor when our system's signals align too closely with recent market moves, which could indicate we are learning from price patterns created by other AI traders rather than fundamentals
4. **Position sizing awareness**: In liquid large-caps (AAPL, MSFT), our trades have negligible market impact. In less liquid names, account for the fact that other AI systems may be executing similar trades simultaneously.

### User Communication
1. Display a "confidence adjustment" factor alongside backtest results that reflects the gap between partial-equilibrium and equilibrium performance
2. Warn users when the system detects high correlation between its recommendations and recent market trends (potential crowded trade)
3. Educate users that AI trading performance in backtests represents an upper bound on live performance

## Cross-References

- [[learning-externality]] — the underlying concept
- [[market-efficiency]] — what the externality degrades
- [[multi-agent-llm-trading]] — the paradigm affected
- [[collusion-awareness]] — related regulatory concern
- [[tradingagents-paper-alignment]] — our implementation context
