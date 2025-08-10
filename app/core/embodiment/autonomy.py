from __future__ import annotations

import asyncio
from typing import Dict, Any
import logging

from .command_bus import EmbodimentCommand, command_bus

logger = logging.getLogger(__name__)


class AutonomyController:
    def __init__(self) -> None:
        self._running: Dict[str, bool] = {}

    async def start(self, agent_id: str, policy: Dict[str, Any] | None = None) -> None:
        self._running[agent_id] = True
        asyncio.create_task(self._loop(agent_id, policy or {}))
        logger.info("[autonomy] started", extra={"agent_id": agent_id})

    async def stop(self, agent_id: str) -> None:
        self._running[agent_id] = False
        logger.info("[autonomy] stopped", extra={"agent_id": agent_id})

    async def _loop(self, agent_id: str, policy: Dict[str, Any]) -> None:
        interval = int(policy.get("interval_seconds", 10))
        prompt = policy.get("prompt", "Introduce yourself briefly.")
        while self._running.get(agent_id, False):
            cmd = EmbodimentCommand(
                agent_id=agent_id,
                action="speak",
                payload={"text": prompt},
                priority=5,
                timeout_ms=8000,
            )
            await command_bus.enqueue(cmd)
            await asyncio.sleep(interval)


autonomy_controller = AutonomyController()



