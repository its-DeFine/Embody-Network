"""VTuber Avatar Control API"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import httpx
import logging

from ..config import settings
from ..dependencies import get_redis, get_current_user
from ..core.orchestration.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/vtuber",
    tags=["VTuber Control"],
    dependencies=[Depends(get_current_user)]
)


class StimulusRequest(BaseModel):
    """Request to send stimulus to VTuber system"""
    content: str
    target_system: Optional[str] = "auto"  # "s1", "s2", or "auto"
    character: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class CharacterSwitch(BaseModel):
    """Request to switch VTuber character"""
    character_name: str
    visual_identity: Optional[str] = None


class VoiceSettings(BaseModel):
    """Voice configuration for VTuber"""
    provider: str = "elevenlabs"  # or "kokoro"
    voice_id: Optional[str] = None
    speed: float = 1.0
    pitch: float = 1.0


class AnimationControl(BaseModel):
    """Animation control parameters"""
    animation_type: str  # "idle", "talking", "gesture", etc.
    intensity: float = 1.0
    duration: Optional[float] = None


@router.post("/stimulus")
async def send_stimulus(request: StimulusRequest):
    """Send a stimulus to the VTuber system"""
    try:
        # Route through orchestrator
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/stimulus",
                json={
                    "content": request.content,
                    "target": request.target_system,
                    "character": request.character,
                    "metadata": request.metadata
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to send stimulus: {e}")
        raise HTTPException(status_code=503, detail="VTuber system unavailable")


@router.post("/character/switch")
async def switch_character(request: CharacterSwitch):
    """Switch the active VTuber character"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/character/switch",
                json={
                    "character": request.character_name,
                    "visual_identity": request.visual_identity
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to switch character: {e}")
        raise HTTPException(status_code=503, detail="Character switch failed")


@router.get("/character/list")
async def list_characters():
    """Get list of available VTuber characters"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/characters"
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError:
        # Return default characters if service unavailable
        return {
            "characters": [
                {"name": "luna", "type": "streamer", "description": "Gaming streamer personality"},
                {"name": "sophia", "type": "educator", "description": "Educational content creator"},
                {"name": "diana", "type": "assistant", "description": "Virtual assistant"}
            ]
        }


@router.post("/voice/settings")
async def update_voice_settings(settings: VoiceSettings):
    """Update VTuber voice settings"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/voice/settings",
                json=settings.dict()
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to update voice settings: {e}")
        raise HTTPException(status_code=503, detail="Voice settings update failed")


@router.post("/animation/control")
async def control_animation(control: AnimationControl):
    """Control VTuber animations"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/animation",
                json=control.dict()
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to control animation: {e}")
        raise HTTPException(status_code=503, detail="Animation control failed")


@router.get("/status")
async def get_vtuber_status():
    """Get current VTuber system status"""
    status = {
        "neurosync_s1": "unknown",
        "autogen_agent": "unknown",
        "scb_gateway": "unknown",
        "active_character": None,
        "voice_provider": None
    }
    
    # Check NeuroSync S1
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"http://{settings.vtuber_host}:{settings.vtuber_port}/health")
            if response.status_code == 200:
                status["neurosync_s1"] = "healthy"
                data = response.json()
                status["active_character"] = data.get("active_character")
    except:
        status["neurosync_s1"] = "unavailable"
    
    # Check AutoGen Agent
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"http://{settings.autogen_host}:{settings.autogen_port}/health")
            if response.status_code == 200:
                status["autogen_agent"] = "healthy"
    except:
        status["autogen_agent"] = "unavailable"
    
    # Check SCB Gateway
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://scb_gateway:8300/health")
            if response.status_code == 200:
                status["scb_gateway"] = "healthy"
    except:
        status["scb_gateway"] = "unavailable"
    
    return status


@router.post("/stream/start")
async def start_streaming(rtmp_url: Optional[str] = None):
    """Start RTMP streaming of VTuber"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/stream/start",
                json={"rtmp_url": rtmp_url or "rtmp://nginx_rtmp:1935/live/stream"}
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to start streaming: {e}")
        raise HTTPException(status_code=503, detail="Streaming start failed")


@router.post("/stream/stop")
async def stop_streaming():
    """Stop RTMP streaming"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.vtuber_host}:{settings.vtuber_port}/stream/stop"
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to stop streaming: {e}")
        raise HTTPException(status_code=503, detail="Streaming stop failed")


@router.get("/cognitive/blackboard")
async def get_cognitive_blackboard():
    """Get current state of the Shared Cognitive Blackboard"""
    redis = await get_redis()
    
    try:
        # Get all keys from SCB namespace
        keys = await redis.keys("scb:*")
        blackboard = {}
        
        for key in keys:
            value = await redis.get(key)
            if value:
                import json
                try:
                    blackboard[key.decode()] = json.loads(value)
                except:
                    blackboard[key.decode()] = value.decode()
        
        return {
            "blackboard": blackboard,
            "total_entries": len(blackboard)
        }
    except Exception as e:
        logger.error(f"Failed to read blackboard: {e}")
        raise HTTPException(status_code=500, detail="Blackboard read failed")


@router.post("/cognitive/write")
async def write_to_blackboard(key: str, value: Dict[str, Any]):
    """Write to the Shared Cognitive Blackboard"""
    redis = await get_redis()
    
    try:
        import json
        await redis.set(f"scb:{key}", json.dumps(value))
        await redis.publish("scb:updates", json.dumps({"key": key, "value": value}))
        
        return {"status": "success", "key": key}
    except Exception as e:
        logger.error(f"Failed to write to blackboard: {e}")
        raise HTTPException(status_code=500, detail="Blackboard write failed")