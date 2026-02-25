from fastapi import FastAPI, Query, HTTPException
import httpx
from datetime import datetime, timezone

app = FastAPI(title="Portfolio Metrics API")

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


@app.get("/portfolio")
async def get_portfolio(
    btc: float = Query(..., description="Amount of BTC held"),
    eth: float = Query(..., description="Amount of ETH held"),
):
    try:
        response = httpx.get(
            COINGECKO_URL,
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"CoinGecko API error: {e.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Could not reach CoinGecko API")

    data = response.json()

    btc_price = data["bitcoin"]["usd"]
    eth_price = data["ethereum"]["usd"]

    btc_value = round(btc * btc_price, 2)
    eth_value = round(eth * eth_price, 2)
    total_value_usd = round(btc_value + eth_value, 2)

    return {
        "btc_value": btc_value,
        "eth_value": eth_value,
        "total_value_usd": total_value_usd,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
