# MarketPilot

> A professional desktop research platform for designing, testing, comparing, and executing rules-based investment strategies.

MarketPilot is a Python application for investors who want to make objective, repeatable investment decisions using systematic strategies instead of emotion.

The project began by implementing the **A-RVol v3** strategy for leveraged ETFs and has since evolved into a modular research platform capable of supporting multiple investment strategies, historical backtesting, benchmarking, portfolio analysis, and eventually live portfolio management.

---

# Vision

MarketPilot is built around four core principles.

## Objectivity

Investment decisions should be driven by predefined rules rather than emotions.

## Transparency

Every recommendation should clearly explain:

- Why it occurred
- Which rules triggered
- What conditions prevented other outcomes

## Reproducible Research

Every strategy should produce identical results when given identical inputs.

Historical testing should always be repeatable.

## Modular Design

Every subsystem should have one responsibility.

Examples:

- Indicators calculate values.
- Signals interpret indicators.
- Strategies make decisions.
- Portfolios manage holdings.
- Reports display results.

Each layer should remain independent of the others.

---

# Documentation

Additional project documentation can be found in the **docs/** folder.

| Document | Purpose |
|----------|---------|
| architecture.md | Overall software architecture |
| roadmap.md | Development roadmap and milestones |
| decisions.md | Architectural decisions and design rationale |
| changelog.md | Project history and completed work |

---

# Current Status

**Version**

0.1.0-alpha

**Current Development Focus**

- Modular Indicator Engine
- Strategy Profile System
- Historical Benchmarking
- Performance Analytics
- Desktop GUI Architecture

---

# Current Features

## Market Data

- Yahoo Finance downloader
- Local data cache
- Historical price validation
- Incremental updates

---

## Backtesting Engine

- Historical replay
- Portfolio simulation
- Trade recording
- Equity curve generation
- Performance statistics

---

## Portfolio Management

- State-based portfolio engine
- Dynamic defensive allocation
- Strategy-specific asset profiles

---

## Performance Analysis

- CAGR
- Total Return
- Maximum Drawdown
- Trade Statistics
- Benchmark Comparison
- Strategy Comparison

---

## Strategies

Implemented

- A-RVol v3 (NASDAQ)
- Buy & Hold

In Progress

- A-RVol v3 (Semiconductors)

Planned

- Kelly 9-SIG
- ATH Drawdown
- Momentum Rotation
- Global ETF Rotation
- Trend Following

---

## Reporting

Current

- Console Report

Planned

- Desktop Dashboard
- Charts
- Portfolio Explorer
- Performance Explorer
- Export to CSV
- PDF Reports

---

# Planned Features

## Dashboard

- Current Market Regime
- Current Portfolio
- Indicator Dashboard
- Strategy Recommendation
- Transition History
- Risk Summary
- Benchmark Comparison
- Equity Curve Charts

---

## Research Lab

- Historical Backtesting
- Parameter Optimization
- Walk-Forward Testing
- Monte Carlo Simulation
- Heatmaps
- Strategy Comparison
- Scenario Analysis

---

## Portfolio Management

- Multiple Brokerage Accounts
- Portfolio Allocation Tracking
- Historical Trade Log
- Asset Allocation Analysis
- Rebalancing Tools

---

## Future Integrations

- Brokerage APIs
- Email Notifications
- Mobile Companion App
- Plugin System
- Cloud Synchronization

---

# Technology

## Current

- Python
- pandas
- numpy
- yfinance

## Planned

- PySide6
- matplotlib
- plotly
- scipy
- pytest

---

# Repository Structure

```
marketpilot/
│
├── application/
├── backtest/
├── benchmarks/
├── comparison/
├── data/
├── defensive/
├── indicators/
├── market/
├── models/
├── performance/
├── portfolio/
├── reports/
├── signals/
├── strategies/
│
docs/
tests/
```

---

# Development Philosophy

MarketPilot follows several long-term design principles.

- Correctness before convenience.
- Keep components loosely coupled.
- Avoid duplicated logic.
- Make every calculation testable.
- Explain every investment decision.
- Prefer readability over cleverness.
- Build features that remain useful for years rather than weeks.

---

# Long-Term Vision

The long-term goal is to build a professional-quality investing workstation.

MarketPilot should eventually become capable of:

- Researching investment ideas
- Comparing strategies
- Optimizing parameters
- Managing multiple portfolios
- Tracking historical performance
- Monitoring live markets
- Producing transparent investment recommendations

while remaining fully modular and independently testable.

---

# License

MIT License (planned)

---

# Disclaimer

MarketPilot is intended for research and educational purposes only.

Nothing in this project constitutes financial, legal, or investment advice.

Users remain solely responsible for their own investment decisions.