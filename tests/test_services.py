import pytest
from unittest.mock import MagicMock, patch

import httpx
from fastapi import HTTPException

from app.services import calculate_portfolio, fetch_prices


class TestCalculatePortfolio:
    prices = {"bitcoin": {"usd": 50000.0}, "ethereum": {"usd": 3000.0}}

    def test_valid_amounts(self):
        result = calculate_portfolio(0.5, 2.0, self.prices)
        assert result["btc_value"] == 25000.0
        assert result["eth_value"] == 6000.0
        assert result["total_value_usd"] == 31000.0

    def test_zero_amounts(self):
        result = calculate_portfolio(0.0, 0.0, self.prices)
        assert result["btc_value"] == 0.0
        assert result["eth_value"] == 0.0
        assert result["total_value_usd"] == 0.0

    def test_rounding(self):
        prices = {"bitcoin": {"usd": 33333.333}, "ethereum": {"usd": 1111.111}}
        result = calculate_portfolio(1.0, 1.0, prices)
        assert result["btc_value"] == 33333.33
        assert result["eth_value"] == 1111.11


class TestFetchPrices:
    def test_http_status_error_raises_502(self):
        mock_response = MagicMock()
        mock_response.status_code = 429
        with patch("app.services.httpx.get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
                "rate limited", request=MagicMock(), response=mock_response
            )
            with pytest.raises(HTTPException) as exc:
                fetch_prices()
            assert exc.value.status_code == 502

    def test_request_error_raises_503(self):
        with patch("app.services.httpx.get") as mock_get:
            mock_get.side_effect = httpx.RequestError("timeout")
            with pytest.raises(HTTPException) as exc:
                fetch_prices()
            assert exc.value.status_code == 503

    def test_returns_price_data(self):
        mock_data = {"bitcoin": {"usd": 50000.0}, "ethereum": {"usd": 3000.0}}
        with patch("app.services.httpx.get") as mock_get:
            mock_get.return_value.raise_for_status = MagicMock()
            mock_get.return_value.json.return_value = mock_data
            result = fetch_prices()
            assert result == mock_data
