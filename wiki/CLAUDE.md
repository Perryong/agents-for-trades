# Trading Knowledge Wiki — Schema

This is a personal financial trading knowledge base maintained by an LLM following the [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The human curates sources and asks questions. The LLM writes and maintains all wiki pages.

## Architecture

```
knowledgebase/          # Raw sources (PDFs, articles). Immutable. LLM reads only.
wiki/                   # LLM-generated markdown. LLM owns this entirely.
  CLAUDE.md             # This file — schema and conventions.
  index.md              # Content catalog — every page with link + one-line summary.
  log.md                # Chronological record of ingests, queries, lint passes.
  overview.md           # High-level synthesis of everything in the wiki.
  sources/              # One summary page per ingested source.
  concepts/             # Topic/concept pages (e.g., implied-volatility.md).
  entities/             # Named entities — people, institutions, models, frameworks.
  strategies/           # Trading strategy pages with entry/exit/risk rules.
  comparisons/          # Side-by-side analyses generated from queries.
  app-notes/            # Actionable notes for improving the agents-for-trades app.
```

## Page Conventions

### Frontmatter (YAML)

Every wiki page starts with YAML frontmatter:

```yaml
---
title: Page Title
type: source | concept | entity | strategy | comparison | app-note | overview
tags: [tag1, tag2]
sources: [source-file-1.pdf, source-file-2.pdf]   # Which raw sources inform this page
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### Cross-references

Use `[[wiki-link]]` syntax for internal links. When a concept is mentioned on any page, link it to its concept page. Example: `[[implied-volatility]]` links to `concepts/implied-volatility.md`.

### Citations

When referencing a raw source, use: `[Source: filename.pdf]` inline. Every factual claim should trace back to at least one source.

## Page Types

### Source summaries (`sources/`)
One page per ingested document. Contains: full citation, abstract/summary, key findings (bulleted), methodology notes, relevance to our trading system, and cross-references to concept/entity pages.

### Concept pages (`concepts/`)
One page per trading concept. Contains: definition, how it works, empirical evidence (with source citations), relevance to our system, open questions. Updated when new sources add information.

### Entity pages (`entities/`)
Named things: models (Black-Scholes, QLBS), frameworks (TradingAgents, Deep Hedging), people, institutions. Contains: description, role in the literature, connections.

### Strategy pages (`strategies/`)
Actionable trading strategies. Contains: setup conditions, entry rules, exit rules, position sizing, risk management, historical evidence, which sources support it.

### Comparison pages (`comparisons/`)
Side-by-side analyses. Generated from queries like "compare X vs Y". Contains: dimensions of comparison, evidence from sources, verdict.

### App notes (`app-notes/`)
Actionable improvements for the agents-for-trades application derived from research. Contains: what to change, why (with source citation), expected impact, implementation notes.

## Operations

### Ingest workflow
1. Read the raw source completely.
2. Create a source summary page in `sources/`.
3. Create or update relevant concept pages in `concepts/`.
4. Create or update relevant entity pages in `entities/`.
5. Extract any actionable trading strategies into `strategies/`.
6. Note any implications for the app in `app-notes/`.
7. Update `index.md` with new/updated pages.
8. Update `overview.md` if the synthesis changes.
9. Append an entry to `log.md`.

### Query workflow
1. Read `index.md` to find relevant pages.
2. Read those pages.
3. Synthesize an answer with citations.
4. If the answer is valuable, file it as a new page (comparison, app-note, etc.).

### Lint workflow
Periodically check for: orphan pages, missing cross-references, contradictions between pages, stale claims superseded by newer sources, concepts mentioned but lacking their own page, data gaps worth investigating.

## Domain Focus

This wiki covers financial trading knowledge relevant to building and improving an AI-powered multi-agent trading system. Key domains:

- **Options trading**: pricing, Greeks, volatility, strategies, microstructure
- **AI/ML in trading**: LLM agents, reinforcement learning, deep learning for finance
- **Market microstructure**: bid-ask spreads, liquidity, order flow, price discovery
- **Risk management**: position sizing, exposure management, regime detection
- **Retail investor behavior**: behavioral biases, common mistakes, edge exploitation
- **Regulatory**: AI collusion, market manipulation, compliance considerations
