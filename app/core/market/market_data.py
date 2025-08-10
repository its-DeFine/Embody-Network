"""
Minimal market data service to satisfy central manager imports and basic health.
Implements async stubs used by management, master, and websocket_manager.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Quote:
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: str


class MarketDataService:
    def __init__(self) -> None:
        self.providers: Dict[str, Dict[str, Any]] = {
            "mock": {"enabled": True, "priority": 1},
        }
        self.crypto_providers: Dict[str, Dict[str, Any]] = {
            "coingecko": {"enabled": False, "priority": 2},
        }
        self.all_providers: Dict[str, Dict[str, Any]] = {
            **self.providers,
            **self.crypto_providers,
        }
        self.primary_provider: str = "mock"
        self.primary_crypto_provider: str = "coingecko"

    # Health and configuration
    async def get_system_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "providers": {
                name: {
                    "status": ("enabled" if cfg.get("enabled") else "disabled"),
                    "success_rate": 100.0 if cfg.get("enabled") else 0.0,
                    "avg_response_time": 5.0,
                    "last_success": datetime.utcnow().isoformat(),
                    "error_count": 0,
                    "circuit_breaker": "closed",
                }
                for name, cfg in self.all_providers.items()
            },
        }

    async def get_active_providers(self) -> List[str]:
        return [name for name, cfg in self.all_providers.items() if cfg.get("enabled")]

    # Data APIs used around the app
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        # Simple deterministic mock that changes slightly over time
        now = datetime.utcnow()
        base = float(abs(hash(symbol)) % 1000) / 10.0 + 50.0
        wiggle = (now.second % 10) * 0.05
        price = round(base + wiggle, 2)
        return Quote(
            symbol=symbol,
            price=price,
            change=round(wiggle, 2),
            change_percent=round((wiggle / max(price - wiggle, 1e-6)) * 100.0, 2),
            volume=100000 + (now.second * 100),
            timestamp=now.isoformat(),
        ).__dict__

    async def get_current_price(self, symbol: str) -> float:
        q = await self.get_quote(symbol)
        return float(q.get("price", 0.0))

    async def get_historical_data(self, symbol: str, period: str, interval: str) -> List[Dict[str, Any]]:
        # Minimal synthetic series
        await asyncio.sleep(0)
        now = datetime.utcnow()
        return [
            {
                "t": (now).isoformat(),
                "o": 100.0,
                "h": 101.0,
                "l": 99.5,
                "c": 100.5,
                "v": 12345,
            }
        ]

    async def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        return {
            "rsi": 50.0,
            "macd": {"macd": 0.0, "signal": 0.0, "hist": 0.0},
            "sma": {"20": 100.0, "50": 100.0, "200": 100.0},
        }


# Global service instance
market_data_service = MarketDataService()



