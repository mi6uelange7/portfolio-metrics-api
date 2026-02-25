import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Query

from app.config import LOG_LEVEL
from app.services import calculate_portfolio, fetch_prices

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio Metrics API")


@app.get("/portfolio")
async def get_portfolio(
    btc: float = Query(..., description="Amount of BTC held"),
    eth: float = Query(..., description="Amount of ETH held"),
):
    logger.info("GET /portfolio | btc=%s eth=%s", btc, eth)
    prices = fetch_prices()
    result = calculate_portfolio(btc, eth, prices)
    return {
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
