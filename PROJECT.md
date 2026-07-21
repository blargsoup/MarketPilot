# MarketPilot Project Roadmap

---

## Current Version

0.1.0-alpha

---

# Project Goal

Build a professional desktop application for researching and executing
rules-based investment strategies.

The application should become a long-term investing workstation rather than
simply a strategy tracker.

---

# Guiding Principles

## Correctness before convenience

Calculations must always be correct before worrying about the interface.

---

## Modular architecture

Every component should have a single responsibility.

Indicators should not know about strategies.

Strategies should not know about the GUI.

The optimizer should use the exact same engine as the dashboard.

---

## Explain every decision

Every recommendation produced by MarketPilot should explain:

- Why the recommendation occurred
- Which rules triggered
- What conditions are still preventing the next transition

---

## Reproducible research

Every backtest and optimization should be reproducible.

The same inputs must always produce the same outputs.

---

# Milestones

## Milestone 1 — Foundation ✅

- [x] Create Git repository
- [x] Create GitHub repository
- [x] Create virtual environment
- [x] Install initial dependencies
- [ ] Create project skeleton
- [ ] Create configuration system
- [ ] Logging
- [ ] Initial unit test framework

---

## Milestone 2 — Data Engine

Goal:

Download and cache market data.

Tasks:

- Yahoo Finance downloader
- Local cache
- Data validation
- Incremental updates

---

## Milestone 3 — Indicator Engine

Implement:

- Realized Volatility (RVol)
- Volatility Ratio (VR)
- SPY Trend
- Credit Stress
- Donchian Channel
- Momentum calculations

---

## Milestone 4 — Strategy Engine

Implement:

A-RVol v3

Features:

- State transitions
- Rule evaluation
- Transition explanations

---

## Milestone 5 — Historical Replay

Replay historical market data day-by-day.

Outputs:

- Trade log
- State history
- Portfolio value
- Performance statistics

---

## Milestone 6 — Desktop Dashboard

Create the first GUI.

Features:

- Current state
- Indicators
- Recommendation
- Transition history

---

## Milestone 7 — Strategy Lab

Implement:

- Backtesting
- Parameter optimization
- Heatmaps
- Walk-forward testing
- Monte Carlo analysis

---

## Future Features

- Kelly 9-SIG
- ATH Drawdown Strategy
- Strategy Builder
- Multiple brokerage accounts
- Notifications
- Plugin system

---

# Coding Standards

- Type hints everywhere
- Docstrings for public functions
- No duplicated logic
- No hard-coded thresholds
- Configuration-driven design

---

# Long-Term Vision

MarketPilot should become a professional-quality investing platform that
can grow indefinitely without requiring major architectural redesign.

The engine should always remain independent of the user interface.