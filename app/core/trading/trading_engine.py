"""
Minimal trading engine implementation for manager QA.
Provides required interfaces referenced by APIs with safe defaults.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict
import logging


logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self) -> None:
        self.is_running: bool = False
        self._started_at: datetime | None = None
        self.portfolio: Any = type("Portfolio", (), {"positions": {}})()
        self._risk_limits: Dict[str, Any] = {
            "max_position_pct": 0.10,
            "daily_trade_limit": 50,
            "stop_loss_pct": 0.02,
        }

    async def start(self, initial_capital: float = 0.0) -> None:
        logger.info("[trading_engine] Starting trading engine", extra={"initial_capital": initial_capital})
        self.is_running = True
        self._started_at = datetime.utcnow()

    async def stop(self) -> None:
        logger.info("[trading_engine] Stopping trading engine")
        self.is_running = False

    async def emergency_stop(self) -> None:
        logger.warning("[trading_engine] EMERGENCY STOP invoked")
        self.is_running = False

    async def cancel_all_orders(self) -> None:
        logger.info("[trading_engine] Cancel all orders called")
        await asyncio.sleep(0)

    async def update_strategy(self, strategy_id: str, config: Dict[str, Any]) -> None:
        logger.info("[trading_engine] Update strategy", extra={"strategy_id": strategy_id, "config": config})
        await asyncio.sleep(0)

    async def get_portfolio_value(self) -> float:
        # Return static value for QA; integrate with positions when implemented
        return 0.0

    async def get_daily_pnl(self) -> float:
        return 0.0

    async def get_risk_limits(self) -> Dict[str, Any]:
        return dict(self._risk_limits)

    async def get_uptime(self) -> str:
        if not self._started_at:
            return "0s"
        delta: timedelta = datetime.utcnow() - self._started_at
        return str(delta)


# Global engine instance
trading_engine = TradingEngine()



