from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional
import logging

import httpx

from ...dependencies import get_redis

logger = logging.getLogger(__name__)


@dataclass
class EmbodimentCommand:
    agent_id: str
    action: str
    payload: Dict[str, Any]
    priority: int = 5
    timeout_ms: int = 5000
    correlation_id: str = ""

    def ensure_correlation(self) -> None:
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


class CommandBus:
    QUEUE_KEY = "embodiment:commands"
    RESULT_PREFIX = "embodiment:command_result:"

    async def enqueue(self, cmd: EmbodimentCommand) -> str:
        cmd.ensure_correlation()
        redis = await get_redis()
        data = asdict(cmd)
        data["enqueued_at"] = datetime.utcnow().isoformat()
        await redis.lpush(self.QUEUE_KEY, json.dumps(data))
        logger.info("[command_bus] enqueued", extra={"cid": cmd.correlation_id, "agent": cmd.agent_id, "action": cmd.action})
        return cmd.correlation_id

    async def dispatch_one(self) -> Optional[Dict[str, Any]]:
        redis = await get_redis()
        raw = await redis.rpop(self.QUEUE_KEY)
        if not raw:
            return None
        data = json.loads(raw)
        result = await self._deliver(data)
        await redis.set(f"{self.RESULT_PREFIX}{data['correlation_id']}", json.dumps(result))
        return result

    async def _deliver(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Fetch agent endpoint from registry
        from .registry import embodiment_registry
        agent = await embodiment_registry.get(data["agent_id"])
        if not agent:
            return {"success": False, "error": "agent_not_found", "data": data}
        endpoint = agent.get("endpoint")
        try:
            async with httpx.AsyncClient(timeout=data.get("timeout_ms", 5000) / 1000.0) as client:
                resp = await client.post(
                    f"{endpoint}/commands",
                    json={"action": data["action"], "payload": data["payload"], "correlation_id": data["correlation_id"]},
                )
                ok = resp.status_code in (200, 202)
                body = resp.json() if ok else {"status_code": resp.status_code, "text": resp.text}
                logger.info("[command_bus] delivered", extra={"cid": data["correlation_id"], "status": ok})
                return {"success": ok, "result": body, "agent_id": data["agent_id"], "correlation_id": data["correlation_id"]}
        except Exception as e:
            logger.error("[command_bus] delivery_error", extra={"cid": data["correlation_id"], "error": str(e)})
            return {"success": False, "error": str(e), "agent_id": data["agent_id"], "correlation_id": data["correlation_id"]}


command_bus = CommandBus()



