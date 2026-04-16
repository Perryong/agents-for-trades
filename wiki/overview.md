---
title: Wiki Overview
type: overview
tags: [overview, synthesis]
sources: [ssrn-6339420.pdf, 2412.20138v7.pdf, w34054.pdf, Sangiorgi_Deep__Learning_to_Trade.pdf]
created: 2026-04-16
updated: 2026-04-16
---

# Trading Knowledge Wiki — Overview

This wiki synthesizes research on AI-powered trading systems, covering our system's foundational architecture, advanced hedging techniques, and systemic risks of AI trading at scale.

## Core Themes

### 1. Our System's Foundation: Multi-Agent LLM Trading

The [[tradingagents-framework]] (Xiao et al., 2025) establishes the architecture our application is built on: specialized LLM agents organized into analyst, researcher, trader, risk management, and fund manager teams. The framework achieves 23-27% cumulative returns over a 3-month backtest, outperforming rule-based baselines by 6-25% with superior Sharpe ratios and controlled drawdown. The key innovation is structured communication (documents and reports rather than raw conversation) combined with adversarial debate (bull/bear researchers, multi-perspective risk team). [Source: 2412.20138v7.pdf]

### 2. Advanced Options Hedging via Reinforcement Learning

Hu et al. (2025) demonstrate that RL-based hedging ([[rlop-model]], [[qlbs-model]]) outperforms traditional [[delta-hedging]] on after-cost metrics, especially during market stress. The critical insight is that static model calibration quality (IVRMSE) does not predict dynamic hedging performance. RLOP's [[shortfall-probability]] objective provides a survival-centric alternative that excels during crises like the 2020 COVID crash. This research informs potential enhancements to our Greeks monitor agent. [Source: ssrn-6339420.pdf]

### 3. Systemic Risks: Collusion and Learning Externalities

Two papers reveal that the widespread adoption of AI trading creates negative systemic effects:

- **[[algorithmic-collusion]]** (Dou et al., 2025): RL trading agents autonomously develop collusive behavior through price-trigger strategies or over-pruning bias, degrading market liquidity, price informativeness, and causing mispricing. This poses regulatory challenges since existing antitrust frameworks require evidence of explicit communication. [Source: w34054.pdf]

- **[[learning-externality]]** (Gufler et al., 2025): Multiple DRL agents trading in a shared market degrade each other's learning through exploratory noise injection into prices. Partial-equilibrium backtests systematically overstate AI performance. This is distinct from collusion — it is a purely informational externality with no strategic benefit to the agents. [Source: Sangiorgi_Deep__Learning_to_Trade.pdf]

## Key Implications for Our System

1. **Backtesting realism**: Our backtests likely overstate live performance. Consider applying performance haircuts and improving slippage modeling.
2. **Regulatory preparedness**: Design for auditability and decision diversity to mitigate collusion risk perception.
3. **Hedging enhancement**: RL-based hedge ratios could substantially improve our options analysis capabilities.
4. **Architecture validation**: Our implementation largely aligns with the validated paper design, with intentional extensions (market analyst, screener, web UI).
5. **Signal diversity**: The learning externality findings reinforce the value of our multi-analyst, adversarial-debate architecture for generating diverse signals.

## Research Gaps

- No papers yet validate multi-agent LLM trading over long time horizons or through major bear markets
- The intersection of LLM-based analysis and RL-based execution remains unexplored
- How the learning externality specifically affects LLM-based (vs. RL-based) trading systems is not yet studied
- Options-specific multi-agent LLM strategies (beyond equity buy/sell/hold) are not covered
