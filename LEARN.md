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

## Phase 5 — Unit Tests

### What I built
Two test files:
- `tests/test_services.py` — unit tests for the service functions directly
- `tests/test_main.py` — endpoint tests via FastAPI's `TestClient`

9 tests total. All of them run without making a single real HTTP request.

### Why tests matter
Here's the thing about untested code — it works until it doesn't, and when it breaks in production, you're debugging live with real consequences. Tests make the failure happen early, locally, when you can still do something about it.

More specifically in a CI/CD context: every push triggers the test stage. If something's broken, the pipeline fails before the code ever gets near a container or a deployment. That's the whole point — catch it early, in isolation, before it becomes someone else's problem.

### What actually gets tested

**`calculate_portfolio` — pure function, no mocking needed**
```python
def test_valid_amounts(self):
    result = calculate_portfolio(0.5, 2.0, prices)
    assert result["total_value_usd"] == 31000.0
```
No HTTP, no I/O, no mocking. Feed it inputs, check the output. This is what pure functions buy you — tests that are trivial to write and impossible to flake.

**`fetch_prices` — mocked HTTP calls**
```python
with patch("app.services.httpx.get") as mock_get:
    mock_get.side_effect = httpx.RequestError("timeout")
    with pytest.raises(HTTPException) as exc:
        fetch_prices()
    assert exc.value.status_code == 503
```
Can't call the real CoinGecko API in tests — it's flaky, rate-limited, and slow. `unittest.mock.patch` swaps out `httpx.get` for a fake that behaves however I tell it to. This lets me test the error handling paths that would be nearly impossible to trigger against a real API.

**Endpoint tests — `TestClient`**
```python
with patch("app.main.fetch_prices", return_value=MOCK_PRICES):
    response = client.get("/portfolio?btc=0.5&eth=2.0")
assert response.status_code == 200
```
FastAPI's `TestClient` wraps the app and lets you send requests without running a server. Combined with mocking `fetch_prices`, I can test the full request/response cycle in pure Python.

### What each test covers
| Test | What it proves |
|------|---------------|
| `test_valid_amounts` | Core math is correct |
| `test_zero_amounts` | Edge case — zero holdings doesn't break anything |
| `test_rounding` | Floating point gets rounded to 2 decimal places |
| `test_http_status_error_raises_502` | Bad API response → correct status code |
| `test_request_error_raises_503` | Network failure → correct status code |
| `test_returns_price_data` | Happy path returns the expected data |
| `test_portfolio_valid_request` | Full endpoint returns correct shape |
| `test_portfolio_zero_values` | Zero amounts work end-to-end |
| `test_portfolio_missing_params` | Missing query params → 422 (FastAPI validation) |

### How tests prevent production failures
The test for missing params is a good example. I didn't write any validation code — FastAPI handles it. But by writing `test_portfolio_missing_params`, I'm asserting that this behavior exists and will keep existing. If someone later strips out the `Query(...)` annotation, that test fails and the pipeline blocks the merge. The contract is enforced automatically.

### Key concepts from this phase
- **pytest** — Python test framework, finds and runs test functions automatically
- **`unittest.mock.patch`** — replaces a real function with a fake for the duration of a test
- **`TestClient`** — sends HTTP requests to the app without a running server
- **Pure function testing** — no setup, no teardown, no mocking needed
- **Mocking** — isolate the unit under test by controlling its dependencies

### Interview talking points
- "I separated unit tests from integration-style tests — service logic gets tested directly, the endpoint gets tested via TestClient"
- "The HTTP calls are mocked — tests don't touch the real CoinGecko API, so they're fast, reliable, and runnable offline"
- "The `calculate_portfolio` function being pure made it trivial to test — that's a direct payoff from the Phase 2 separation"
- "The 422 test isn't testing my code — it's testing that FastAPI's validation is wired up correctly, which is still worth having"

---

## Phase 6 + 7 — Docker and CI/CD

### What I built
- `Dockerfile` — packages the app into a container image
- `.gitlab-ci.yml` — two-stage pipeline: test then build

These two belong together. The whole point of the CI pipeline is to test the code and then build a verified image. One without the other is incomplete.

### What Docker actually is
Docker packages an application and everything it needs to run — the runtime, dependencies, config — into a single portable unit called a container image.

Before containers, deploying Python meant: install Python, install the right version of Python, set up a virtualenv, install dependencies, configure environment variables, hope the server's OS doesn't interfere. Now it means: `docker run`.

The image is built once and runs identically everywhere — on your laptop, on a CI runner, in production. That's the value. Not "it works on my machine" — it works in the image, and the image runs anywhere.

### Reading the Dockerfile
```dockerfile
FROM python:3.11-slim          # base image — Python 3.11 on minimal Debian
WORKDIR /app                   # all commands run from here inside the container
COPY requirements.txt .        # copy this first — layer caching
RUN pip install --no-cache-dir -r requirements.txt  # install deps
COPY app/ ./app/               # copy app code after deps (cache optimization)
EXPOSE 8000                    # documents the port — doesn't actually open it
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The ordering of `COPY requirements.txt` before `COPY app/` is intentional. Docker builds images in layers and caches each one. Dependencies change rarely. App code changes constantly. By copying `requirements.txt` first and installing before copying the code, Docker can skip the `pip install` step on rebuilds as long as the requirements haven't changed. This makes builds significantly faster.

### Container isolation
The container runs in its own filesystem, network namespace, and process space. It can only see what you explicitly give it. This matters for security — a compromised container can't easily reach the host or other containers. It also means the app behaves the same regardless of what else is running on the host.

### The CI/CD pipeline

```yaml
stages:
  - test
  - docker-build
```

Two stages, run in order. If `test` fails, `docker-build` never runs. You never ship a broken image.

**test stage:**
```yaml
test:
  image: python:3.11-slim
  before_script:
    - pip install -r requirements.txt
  script:
    - pytest tests/ -v
```
Spins up a fresh Python container on every push, installs dependencies, runs the test suite. If any test fails, the stage fails and GitLab marks the pipeline red. The `docker-build` stage doesn't execute.

**docker-build stage:**
```yaml
docker-build:
  image: docker:24
  services:
    - docker:24-dind        # Docker-in-Docker — lets CI build Docker images
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
  only:
    - main                  # only build images from main branch
```
`$CI_REGISTRY_IMAGE` and `$CI_COMMIT_SHORT_SHA` are GitLab's built-in variables. Every merge to main gets its own tagged image. If something goes wrong, you can pull any previous image by its commit SHA and roll back.

### What happens on a push
```
git push
      |
GitLab detects the push
      |
Pipeline triggers
      |
Stage 1: test
  → fresh container spins up
  → pip install
  → pytest runs
  → if any test fails → pipeline fails, nothing ships
      |
Stage 2: docker-build (only if test passed)
  → docker build
  → image tagged with commit SHA
  → pushed to GitLab container registry
      |
Image is ready to deploy
```

### Why CI reduces operational risk
Without CI, the flow is: write code → push → manually test → manually build → deploy → find out it was broken. Every one of those manual steps is a place where things get skipped when you're in a hurry.

With CI, the flow is: push → pipeline either passes or fails. No manual steps. No "I'll test it after". The tests run on every push whether you remember to or not. The image only gets built if the tests pass. It's not about distrust — it's about not relying on memory and discipline to catch things that a machine can catch automatically.

### Key concepts from this phase
- **Docker** — packages app + runtime into a portable container image
- **Dockerfile** — instructions for building the image
- **Layer caching** — ordering COPY/RUN to maximize cache hits on rebuilds
- **Container isolation** — own filesystem, network, process space
- **CI/CD** — automated pipeline triggered on push
- **Pipeline stages** — ordered, each stage gates the next
- **Docker-in-Docker (dind)** — lets CI runners build Docker images
- **Image tagging by commit SHA** — enables precise rollbacks

### Interview talking points
- "The Dockerfile copies requirements before code — intentional for layer caching, keeps rebuilds fast when only app code changes"
- "The CI pipeline has two stages — test gates the build. A failing test means no image gets produced, so broken code can't ship"
- "Images are tagged with the commit SHA, not `latest` — that means every deployment is traceable back to an exact commit and rollbacks are a single command"
- "Docker-in-Docker lets the CI runner build and push container images without needing Docker pre-installed on the host"

---

<!-- Phase 8 content will be appended here -->
