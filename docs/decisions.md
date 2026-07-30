# Architecture Decisions

---

## Decision 001

Indicators calculate from OHLCV data.

Reason

Never depend on precomputed CSV columns.

---

## Decision 002

Strategies never calculate indicators.

Reason

Single responsibility.

---

## Decision 003

Signals convert indicators into booleans.

Reason

Strategies remain readable.

---

## Decision 004

Portfolio owns all equity calculations.

Reason

One source of truth.

---

## Decision 005

Every strategy uses the same backtest engine.

Reason

Fair comparison.

---

## Decision 006

Performance calculations occur after the backtest.

Reason

Keeps the engine deterministic.

---

## Decision 007

GUI never performs calculations.

Reason

Presentation only.

---

## Decision 008

Profiles define investable universes.

Examples

NASDAQ

Semiconductors

Future:

World

Canada

Crypto
