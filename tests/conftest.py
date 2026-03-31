import pytest


@pytest.fixture
def mock_tradier_chain_response():
    """Dict matching Tradier chain JSON structure with 2 contracts, each having greeks."""
    return {
        "options": {
            "option": [
                {
                    "symbol": "AAPL240119C00150000",
                    "option_type": "call",
                    "strike": 150.0,
                    "expiration_date": "2024-01-19",
                    "bid": 1.50,
                    "ask": 1.60,
                    "volume": 100,
                    "open_interest": 500,
                    "underlying": 155.0,
                    "greeks": {
                        "delta": 0.55,
                        "gamma": 0.03,
                        "theta": -0.05,
                        "vega": 0.12,
                        "smv_vol": 0.28,
                        "mid_iv": 0.27,
                    },
                },
                {
                    "symbol": "AAPL240119P00150000",
                    "option_type": "put",
                    "strike": 150.0,
                    "expiration_date": "2024-01-19",
                    "bid": 0.90,
                    "ask": 1.00,
                    "volume": 80,
                    "open_interest": 300,
                    "underlying": 155.0,
                    "greeks": {
                        "delta": -0.45,
                        "gamma": 0.03,
                        "theta": -0.04,
                        "vega": 0.11,
                        "smv_vol": 0.29,
                        "mid_iv": 0.28,
                    },
                },
            ]
        }
    }


@pytest.fixture
def mock_tradier_expirations_response():
    """Dict matching Tradier expirations JSON with list of dates."""
    return {
        "expirations": {
            "date": ["2024-01-19", "2024-02-16", "2024-03-15"]
        }
    }


@pytest.fixture
def mock_tradier_single_contract_response():
    """Dict where options.option is a single dict (not a list)."""
    return {
        "options": {
            "option": {
                "symbol": "AAPL240119C00150000",
                "option_type": "call",
                "strike": 150.0,
                "expiration_date": "2024-01-19",
                "bid": 1.50,
                "ask": 1.60,
                "volume": 100,
                "open_interest": 500,
                "underlying": 155.0,
                "greeks": {
                    "delta": 0.55,
                    "gamma": 0.03,
                    "theta": -0.05,
                    "vega": 0.12,
                    "smv_vol": 0.28,
                    "mid_iv": 0.27,
                },
            }
        }
    }


@pytest.fixture
def mock_tradier_null_greeks_response():
    """Dict where greeks is None on each contract."""
    return {
        "options": {
            "option": [
                {
                    "symbol": "AAPL240119C00150000",
                    "option_type": "call",
                    "strike": 150.0,
                    "expiration_date": "2024-01-19",
                    "bid": 1.50,
                    "ask": 1.60,
                    "volume": 100,
                    "open_interest": 500,
                    "underlying": 155.0,
                    "greeks": None,
                },
                {
                    "symbol": "AAPL240119P00150000",
                    "option_type": "put",
                    "strike": 150.0,
                    "expiration_date": "2024-01-19",
                    "bid": 0.90,
                    "ask": 1.00,
                    "volume": 80,
                    "open_interest": 300,
                    "underlying": 155.0,
                    "greeks": None,
                },
            ]
        }
    }
