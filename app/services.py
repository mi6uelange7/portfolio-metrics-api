import httpx
import logging
from fastapi import HTTPException

from app.config import COINGECKO_BASE_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def fetch_prices() -> dict:
    logger.info(
        "Fetching prices from CoinGecko | url=%s timeout=%s",
        COINGECKO_BASE_URL,
        REQUEST_TIMEOUT,
    )
    try:
        response = httpx.get(
            COINGECKO_BASE_URL,
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "CoinGecko returned bad status | status=%s", e.response.status_code
        )
        raise HTTPException(
            status_code=502,
            detail=f"CoinGecko API error: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error("Failed to reach CoinGecko | error=%s", e)
        raise HTTPException(
            status_code=503,
            detail="Could not reach CoinGecko API",
        )

    logger.info("CoinGecko prices fetched successfully")
    return response.json()


def calculate_portfolio(btc: float, eth: float, prices: dict) -> dict:
    btc_price = prices["bitcoin"]["usd"]
    eth_price = prices["ethereum"]["usd"]

    btc_value = round(btc * btc_price, 2)
    eth_value = round(eth * eth_price, 2)
    total_value_usd = round(btc_value + eth_value, 2)

    logger.info(
        "Portfolio calculated | btc=%.4f eth=%.4f total_usd=%.2f",
        btc,
        eth,
        total_value_usd,
    )
    return {
        "btc_value": btc_value,
        "eth_value": eth_value,
        "total_value_usd": total_value_usd,
    }
