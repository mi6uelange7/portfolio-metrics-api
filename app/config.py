import os
from dotenv import load_dotenv

load_dotenv()

COINGECKO_BASE_URL: str = os.getenv(
    "COINGECKO_BASE_URL",
    "https://api.coingecko.com/api/v3/simple/price",
)

REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "10.0"))

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
