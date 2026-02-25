# LEARN.md — Containerized Portfolio Metrics API

A running log of what I built, why I built it, and what it taught me.
The goal here isn't just to ship code — it's to understand it well enough to talk about it clearly.

---

## Architecture Overview

```
Client (browser / curl / Postman)
        |
        v
  FastAPI App  (/portfolio?btc=X&eth=Y)
        |
        v
  CoinGecko API  (live BTC + ETH prices)
        |
        v
  JSON Response  (btc_value, eth_value, total_value_usd, timestamp)
```

---

## Project File Map

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app + route handlers |
| `app/services.py` | Business logic (price fetching, calculations) |
| `app/config.py` | Environment-based config |
| `app/__init__.py` | Makes `app/` a Python package |
| `requirements.txt` | Python dependencies |
| `tests/test_main.py` | Unit tests |
| `Dockerfile` | Container definition |
| `.gitlab-ci.yml` | CI/CD pipeline |
| `.env.example` | Template for environment variables |

---

## Phase 1 — Basic FastAPI Service

### What I built
A single FastAPI endpoint: `GET /portfolio?btc=<float>&eth=<float>`

It hits the CoinGecko public API, grabs live BTC and ETH prices, multiplies them by the amounts I pass in, and returns a clean JSON response with the values and a UTC timestamp.

### What FastAPI actually is
FastAPI is a Python web framework built on top of Starlette and Pydantic. What makes it worth using over something like Flask is that it:
- Automatically validates query params and request bodies using Python type hints
- Generates interactive API docs at `/docs` out of the box (Swagger UI)
- Is async-native, meaning it can handle concurrent requests without blocking

When I write `btc: float = Query(...)`, FastAPI handles all the validation. If someone sends a string instead of a number, it returns a 422 before my code even runs. That's huge — I'm not writing validation boilerplate by hand.

### How a request actually flows
```
GET /portfolio?btc=0.5&eth=2.0
        |
FastAPI receives it
        |
Type validation runs (btc and eth must be floats)
        |
Route handler executes
        |
httpx makes a GET request to CoinGecko
        |
Response parsed → values calculated
        |
JSON returned to client
```

### Why service separation matters (even at this stage)
Right now the logic is all in `main.py`. That's fine for Phase 1 — it's readable and straightforward. But as soon as I need to test the calculation logic without making a real HTTP call, or I want to swap out CoinGecko for another price API, having it all in the route handler becomes a problem.

Separation of concerns isn't about making things complex — it's about making them swappable and testable. Phase 2 fixes this.

### Error handling here
Even in Phase 1, I'm not just letting exceptions crash the app. I catch two things:
- `HTTPStatusError` — CoinGecko responded but with a bad status (4xx/5xx)
- `RequestError` — couldn't reach CoinGecko at all (timeout, DNS, etc.)

Both get converted into proper HTTP responses (502 and 503) with readable error messages. This is the difference between a service that fails gracefully and one that throws a 500 with a Python traceback at whoever's calling it.

### Key concepts from this phase
- **FastAPI** — async Python web framework with automatic validation
- **Query parameters** — `?btc=0.5&eth=2.0` — extracted and typed automatically
- **httpx** — modern async-capable HTTP client for Python (better than requests for FastAPI)
- **HTTP status codes** — 200 OK, 502 Bad Gateway, 503 Service Unavailable
- **UTC timestamps** — always use UTC in APIs. Timezones are a production debugging nightmare.

### Interview talking points
- "I used FastAPI because it gives me type safety and auto-validation without writing boilerplate"
- "I separated error cases — network failures vs. bad API responses — and mapped them to appropriate HTTP status codes"
- "httpx over requests because it supports async natively, which pairs better with FastAPI's async route handlers"

---

<!-- Phase 2 content will be appended here -->
