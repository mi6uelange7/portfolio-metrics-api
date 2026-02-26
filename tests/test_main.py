from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_PRICES = {"bitcoin": {"usd": 50000.0}, "ethereum": {"usd": 3000.0}}


def test_portfolio_valid_request():
    with patch("app.main.fetch_prices", return_value=MOCK_PRICES):
        response = client.get("/portfolio?btc=0.5&eth=2.0")
    assert response.status_code == 200
    data = response.json()
    assert data["btc_value"] == 25000.0
    assert data["eth_value"] == 6000.0
    assert data["total_value_usd"] == 31000.0
    assert "timestamp" in data


def test_portfolio_zero_values():
    with patch("app.main.fetch_prices", return_value=MOCK_PRICES):
        response = client.get("/portfolio?btc=0&eth=0")
    assert response.status_code == 200
    assert response.json()["total_value_usd"] == 0.0


def test_portfolio_missing_params():
    response = client.get("/portfolio")
    assert response.status_code == 422
