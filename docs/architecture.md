# Architecture

## Design Philosophy

Every subsystem has one responsibility.

MarketPilot is built in layers.

```
GUI
│
Application
│
Reports
│
Strategies
│
Signals
│
Indicators
│
Market Data
```

---

# Modules

## Data

Responsible for:

- Downloading data
- Cache management
- Validation

Output:

MarketHistory

---

## Indicators

Responsible for ALL calculations.

Examples:

- Moving averages
- RVol
- Volatility Ratio
- Credit Stress
- Donchian
- Momentum

Indicators operate only on OHLCV data.

No strategy logic belongs here.

---

## Signals

Converts indicators into rule thresholds.

Example:

RVol = 21%

↓

rvol_over_qld = True

Signals contain no investment decisions.

---

## Strategies

Convert signals into portfolio actions.

Example:

TQQQ

↓

QLD

↓

Defensive

Strategies never calculate indicators.

---

## Portfolio

Responsible for:

- Holdings
- Equity
- Position changes

---

## Backtesting

Responsible for replaying market history.

Produces:

- Equity curve
- Trades
- Simulation timeline

---

## Performance

Responsible for:

- CAGR
- Drawdown
- Trade analysis
- Benchmark comparison

---

## Reports

Current:

Console

Future:

GUI
PDF
CSV