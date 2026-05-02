# Bybit Trading Terminal v117 — Tester Guide (EN)

## 1. Overview

This is a local web-based crypto trading terminal combining:

- Market structure analysis
- Orderflow / Delta
- Smart Zones
- Pattern & Phase Engines
- Decision Engine v3
- ML + Ensemble layer
- Explainability UI
- Performance Logging
- PnL Tracking

Runs locally in browser.

---

## 2. Requirements

- Python 3.10+
- Internet
- Chrome / Edge / Safari

Install:

pip install -r requirements.txt

---

## 3. Run

python main.py

Open:
http://localhost:5000

---

## 4. Core Features

### Dashboard
- Signals
- Direction (LONG/SHORT)
- Probability / EV
- Smart Zones
- ML scoring

### Chart Window
- Candles, EMA, RSI
- Entry / TP / SL
- Orderflow / DOM
- Decision Engine
- Explainability
- PnL / Stats

---

## 5. Decision Engine v3

Outputs:
- probability
- EV
- action: TRADE / WAIT / NO_TRADE / BLOCKED
- grade

---

## 6. ML / Ensemble

Combines:
- ML model (LightGBM)
- rule-based logic

Fallback safe if model missing.

---

## 7. Explainability

Shows top factors influencing decision.

---

## 8. Performance Logging

Saved in:
logs/performance.jsonl

---

## 9. PnL Engine

Tracks trades:
logs/trades.jsonl

API:
/api/pnl

---

## 10. Stats

Shows:
- trades
- winrate
- pnl

---

## 11. Testing

1. Run app
2. Open dashboard
3. Open charts
4. Check signals
5. Check PnL & Stats

---

## 12. Limitations

- No real exchange execution
- Simulated PnL
- No fees/slippage

---

## 13. Disclaimer

For research/testing only. Not financial advice.
