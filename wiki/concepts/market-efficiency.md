---
title: Market Efficiency
type: concept
tags: [market-efficiency, EMH, AI-trading, price-discovery, liquidity]
sources: [w34054.pdf, Sangiorgi_Deep__Learning_to_Trade.pdf]
created: 2026-04-16
updated: 2026-04-16
---

## Definition

Market efficiency, rooted in the Efficient Market Hypothesis (EMH), describes the degree to which asset prices reflect available information. In an efficient market, prices fully incorporate all relevant information, making it impossible to consistently achieve excess returns. Key measures include price informativeness (how much of fundamental value is reflected in prices), return predictability (lower is more efficient), and liquidity (inversely related to price response to supply shocks).

## How AI Trading Affects Market Efficiency

Recent research reveals a complex and sometimes contradictory picture of AI's impact on market efficiency.

### Positive Effects (Individual AI Traders)

Gufler, Sangiorgi & Tarantino (2025) show that individual AI traders, when operating in isolation or small numbers, improve market outcomes:
- They reduce the share of returns explained by public signals (prices become more efficient). [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- They improve liquidity by attenuating price responses to transitory supply shocks. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Their behavior qualitatively matches the rational benchmark's predictions. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

### Negative Effects (Multiple AI Traders)

Two distinct mechanisms degrade market efficiency when multiple AI traders interact:

**1. [[learning-externality]] (Gufler et al., 2025)**
As the number of AI traders or their collective wealth share grows, exploratory trades inject noise into prices, and learned policies become suboptimal:
- Return predictability remains elevated relative to the rational benchmark. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- Prices react more sharply to transitory supply shocks (lower liquidity). [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]
- AI traders leave exploitable patterns in the market that fully rational agents would eliminate. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

**2. [[algorithmic-collusion]] (Dou et al., 2025)**
When RL agents develop collusive behavior (through price-trigger strategies or over-pruning bias), the effects on market efficiency are uniformly negative:
- Lower market liquidity (informed traders withhold trading activity). [Source: w34054.pdf]
- Lower price informativeness (prices reflect less fundamental information). [Source: w34054.pdf]
- Higher mispricing (larger deviations between prices and fundamental values). [Source: w34054.pdf]
- These effects hold regardless of which collusion mechanism is at work. [Source: w34054.pdf]

### Key Insight: Partial-Equilibrium Overstatement

A critical finding across both papers is that partial-equilibrium analysis (backtesting on fixed historical data where the AI's trades do not affect prices) systematically overstates both AI profitability and its positive impact on market efficiency. Only equilibrium analysis that accounts for endogenous price effects captures the true picture. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Implications

1. The widespread adoption of AI trading is not guaranteed to improve market quality.
2. Regulators should consider the collective effects of AI trading, not just individual agent behavior.
3. AI trading system designers should account for the fact that their strategies will be less effective in live markets than backtests suggest.
4. There may be an optimal "density" of AI traders beyond which additional adoption degrades rather than improves market quality.

## Relevance to Our System

Our [[tradingagents-framework]] operates in markets alongside other algorithmic and AI traders. Understanding that our backtests likely overstate performance is important for setting realistic expectations. The collusion findings suggest designing our system to avoid behavioral patterns that could be interpreted as coordinated.

## Cross-References

- [[algorithmic-collusion]] — one mechanism degrading efficiency
- [[learning-externality]] — another mechanism degrading efficiency
- [[collusion-awareness]] — regulatory design considerations
- [[learning-externality-mitigation]] — mitigating multi-agent degradation
