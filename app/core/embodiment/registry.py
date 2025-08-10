from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from ...dependencies import get_redis

logger = logging.getLogger(__name__)


@dataclass
class EmbodiedAgent:
    agent_id: str
    name: str
    endpoint: str
    capabilities: List[str]
    orchestrator_id: Optional[str] = None
    last_heartbeat: Optional[str] = None
    status: str = "unknown"
    metadata: Dict[str, Any] = None


class EmbodimentRegistry:
    KEY_PREFIX = "embodiment:agent:"

    async def register(self, agent: EmbodiedAgent) -> bool:
        redis = await get_redis()
        key = f"{self.KEY_PREFIX}{agent.agent_id}"
        data = asdict(agent)
        if data.get("metadata") is None:
            data["metadata"] = {}
        data["registered_at"] = datetime.utcnow().isoformat()
        await redis.set(key, json.dumps(data))
        logger.info("[registry] registered agent", extra={"agent_id": agent.agent_id})
        return True

    async def heartbeat(self, agent_id: str, status: str = "online", metadata: Dict[str, Any] = None) -> bool:
        redis = await get_redis()
        key = f"{self.KEY_PREFIX}{agent_id}"
        val = await redis.get(key)
        if not val:
            return False
        obj = json.loads(val)
        obj["last_heartbeat"] = datetime.utcnow().isoformat()
        obj["status"] = status
        if metadata:
            meta = obj.get("metadata", {})
            meta.update(metadata)
            obj["metadata"] = meta
        await redis.set(key, json.dumps(obj))
        return True

    async def list_agents(self) -> List[Dict[str, Any]]:
        redis = await get_redis()
        keys = await redis.keys(f"{self.KEY_PREFIX}*")
        result: List[Dict[str, Any]] = []
        for key in keys:
            raw = await redis.get(key)
            if raw:
                result.append(json.loads(raw))
        return result

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        redis = await get_redis()
        raw = await redis.get(f"{self.KEY_PREFIX}{agent_id}")
        return json.loads(raw) if raw else None


embodiment_registry = EmbodimentRegistry()



