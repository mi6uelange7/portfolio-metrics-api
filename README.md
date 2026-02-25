# Portfolio Metrics API

A FastAPI service that takes how much BTC and ETH you're holding, hits the CoinGecko API for live prices, and returns your portfolio value in USD.

Built as a learning project — the goal is a production-grade containerized API with proper structure, logging, config management, tests, and a CI/CD pipeline. Building it phase by phase.

---

## What it does

```
GET /portfolio?btc=0.5&eth=2.0
```

```json
{
  "btc_value": 47823.15,
  "eth_value": 6201.40,
  "total_value_usd": 54024.55,
  "timestamp": "2026-02-25T12:00:01.000000+00:00"
}
```

---

## Running locally

```bash
# install dependencies
pip install -r requirements.txt

# copy env template and adjust if needed
cp .env.example .env

# start the server
uvicorn app.main:app --reload
```

API is at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

---

## Project structure

```
app/
  main.py       # route handlers, logging setup
  services.py   # business logic — price fetching, calculations
  config.py     # environment-based config
  __init__.py
.env.example    # environment variable template
requirements.txt
LEARN.md        # detailed notes on every phase — what was built and why
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COINGECKO_BASE_URL` | CoinGecko v3 simple/price | Price API endpoint |
| `REQUEST_TIMEOUT` | `10.0` | HTTP timeout in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, ERROR) |

---

## Roadmap

- [x] Phase 1 — Basic FastAPI endpoint
- [x] Phase 2 — Service layer (separated business logic)
- [x] Phase 3+4 — Structured logging + environment config
- [ ] Phase 5 — Unit tests
- [ ] Phase 6 — Dockerfile + containerization
- [ ] Phase 7 — CI/CD pipeline
