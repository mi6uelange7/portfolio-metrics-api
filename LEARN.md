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

## Phase 2 — Separate Business Logic

### What changed
Pulled the price-fetching and calculation logic out of `main.py` and into `app/services.py`. The route handler now does exactly one thing: receive the request, call the service, return the response.

```
main.py         →  route definition, logging setup, returning responses
services.py     →  fetching prices, calculating portfolio values
config.py       →  environment-based configuration
```

### Why route handlers shouldn't hold business logic
The route handler is the HTTP layer. Its job is to deal with the request/response cycle — read the inputs, hand them off, send something back. That's it. When the actual work (API calls, calculations, data transformations) also lives in there, a few problems show up fast:

1. **Can't test logic without simulating HTTP** — if the calculation is inside the route, writing a unit test for it means spinning up the full request pipeline. Moving it to a function means I can call it directly.

2. **Can't swap dependencies easily** — right now it's CoinGecko. Next month it might be something else. If the fetch logic is in a service, I change one function. If it's tangled up in the route, I'm untangling a mess.

3. **Harder to read** — fat route handlers are a wall of code. Slim ones are self-documenting. `prices = fetch_prices()` tells you exactly what's happening.

### Separation of concerns
This is a core design principle. Each part of the code should have one clearly defined responsibility, and should not need to know about how other parts work internally.

`main.py` doesn't know how prices are fetched. It doesn't care. It just calls `fetch_prices()` and trusts it to return a dict. That separation is what makes the code replaceable, testable, and readable.

### What services.py actually does
Two functions:

- `fetch_prices()` — hits CoinGecko, handles both types of failure (bad status, connection error), logs what it's doing, returns raw price data
- `calculate_portfolio(btc, eth, prices)` — pure math. Takes amounts and prices, returns calculated values. No HTTP, no I/O, no side effects

That second function being pure is important. A function with no side effects is trivial to test — same inputs always give same outputs.

### Error handling here
The error handling from Phase 1 lives in `services.py` now. Still catching the same two cases:
- `HTTPStatusError` → 502 (CoinGecko responded but something's wrong on their end)
- `RequestError` → 503 (couldn't reach CoinGecko at all)

The route handler doesn't need to know about these. If `fetch_prices()` raises an `HTTPException`, FastAPI catches it and returns the appropriate response automatically.

### Key concepts from this phase
- **Separation of concerns** — each module has one job
- **Service layer** — where business logic lives, decoupled from HTTP
- **Pure functions** — same inputs, same outputs, no side effects. easy to test.
- **Dependency inversion** — route depends on the service interface, not the implementation

### Interview talking points
- "I separated the HTTP layer from the business logic — the route handler delegates to service functions, it doesn't do the work itself"
- "The calculation function is pure — no I/O, no side effects — which means I can unit test it without mocking anything"
- "This structure makes it straightforward to swap out CoinGecko for another price source without touching the route layer"

---

## Phase 3 + 4 — Logging and Environment Config

### What changed
Two things added together because they're tightly coupled:

- `app/config.py` — loads config from environment variables
- Logging setup in `main.py` — `LOG_LEVEL` is itself an env var, so you can't really do one without the other

Also added `.env.example` as a template for what variables the app expects.

### config.py — why it exists
Before this, the API URL and timeout were hardcoded in `main.py`. That's fine for a first draft but it creates real problems:

- Can't change behavior between environments (dev vs prod vs CI) without editing code
- Secrets (API keys, DB passwords) end up in version control
- Every config change requires a redeploy of code that didn't actually change

`config.py` reads three values from the environment, with sensible defaults if they're not set:

```python
COINGECKO_BASE_URL  →  where to hit the API
REQUEST_TIMEOUT     →  how long to wait before giving up
LOG_LEVEL           →  how verbose the logs should be
```

`python-dotenv` is doing the work of loading a `.env` file if it exists. In production you'd use actual environment variables — the `.env` file is just a dev convenience.

### The 12-factor app
This config pattern comes from the [12-factor app methodology](https://12factor.net/config). The relevant principle is: **store config in the environment, not the code.**

The reasoning — an app's config changes between deployments (staging vs prod, different API keys, different timeouts). The code doesn't. So they shouldn't be in the same place. Environment variables are the standard mechanism for this because they're:
- OS-level, no file needed
- Not checked into source control by default
- Easy to inject in containers and CI systems

### .env.example
The actual `.env` file is in `.gitignore` (it would hold real secrets in a real project). `.env.example` is the committed version — it tells whoever's setting up the project what variables they need, without exposing real values.

### Logging — why it matters
`print()` statements work locally. They don't work in production. Here's what's missing:
- No timestamps
- No severity level — can't tell if it's info or an error
- No source — which file, which function
- No way to filter — can't say "only show me errors"

Python's `logging` module fixes all of that. The setup in `main.py`:

```python
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
```

Every log line now looks like:
```
2026-02-25 12:00:01 | INFO | app.services | CoinGecko prices fetched successfully
2026-02-25 12:00:01 | ERROR | app.services | CoinGecko returned bad status | status=429
```

That's a log line you can actually use. The timestamp tells you when. The level tells you severity. The name tells you where in the code.

### Log levels
| Level | When to use |
|-------|-------------|
| `DEBUG` | Detailed internals, only useful while actively debugging |
| `INFO` | Normal operations — requests coming in, calls succeeding |
| `WARNING` | Something unexpected but not broken |
| `ERROR` | Something failed, needs attention |
| `CRITICAL` | Service is down |

In production, you'd typically run at `INFO`. In dev you might drop to `DEBUG` to see everything. Setting `LOG_LEVEL=ERROR` in a noisy environment cuts down the noise to only what needs fixing.

Because `LOG_LEVEL` is an environment variable, you can change the log verbosity without touching any code. Just update the env var and restart.

### Structured logging (key=value format)
The log messages in `services.py` use a key=value format:

```python
logger.info("Fetching prices from CoinGecko | url=%s timeout=%s", COINGECKO_BASE_URL, REQUEST_TIMEOUT)
```

This is structured logging — formatting log output so it's machine-parseable as well as human-readable. Tools like Datadog, Splunk, or even basic `grep` can pull out specific fields. When you're searching through a million log lines for all requests where `total_usd > 50000`, structured logs make that query possible.

### Key concepts from this phase
- **Environment variables** — runtime config that lives outside the codebase
- **12-factor app** — methodology for building portable, deployable software
- **python-dotenv** — loads `.env` files into the environment for local dev
- **Python logging module** — structured, leveled, configurable logging
- **Log levels** — INFO, ERROR, DEBUG etc. — filter signal from noise
- **Structured logs** — key=value format, machine-parseable

### Interview talking points
- "Config lives in environment variables, not in code — so I can deploy the same artifact to dev, staging, and prod without changing source"
- "I used Python's standard logging module over print statements — timestamps, severity levels, and source context are all there out of the box"
- "Log level is itself configurable via env var — so I can crank up verbosity in dev and keep it quiet in prod without touching the code"
- "The key=value log format is intentional — structured logs are parseable by log aggregation tools, which matters when you're searching through real production traffic"

---

<!-- Phase 5 content will be appended here -->
