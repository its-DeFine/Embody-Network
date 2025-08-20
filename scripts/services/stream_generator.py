#!/usr/bin/env python3
"""
Stream Generator Service
Sends test streams to Livepeer Gateway to trigger actual payment flow
"""

import asyncio
import httpx
import logging
import os
import time
import subprocess
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StreamGenerator:
    """Generates test streams to trigger Livepeer payments"""
    
    def __init__(self):
        self.gateway_rtmp = os.environ.get("GATEWAY_RTMP", "rtmp://livepeer-gateway:1935/live")
        self.gateway_http = os.environ.get("GATEWAY_HTTP", "http://livepeer-gateway:8935")
        self.stream_duration = int(os.environ.get("STREAM_DURATION_SECONDS", "30"))
        self.stream_interval = int(os.environ.get("STREAM_INTERVAL_SECONDS", "60"))
        self.test_pattern = os.environ.get("TEST_PATTERN", "testsrc2")
        
    async def check_orchestrator_status(self) -> Dict[str, Any]:
        """Check if orchestrators are available"""
        try:
            async with httpx.AsyncClient() as client:
                # Check gateway status
                response = await client.get(f"{self.gateway_http}/status")
                if response.status_code == 200:
                    data = response.json()
                    orchestrators = data.get("OrchestratorPool", [])
                    logger.info(f"Found {len(orchestrators)} orchestrators in pool")
                    return {
                        "available": len(orchestrators) > 0,
                        "count": len(orchestrators),
                        "orchestrators": orchestrators
                    }
        except Exception as e:
            logger.error(f"Failed to check orchestrator status: {e}")
        
        return {"available": False, "count": 0, "orchestrators": []}
    
    async def generate_test_stream(self, stream_key: str = "test"):
        """Generate a test video stream using FFmpeg"""
        logger.info(f"Starting test stream to {self.gateway_rtmp}/{stream_key}")
        
        # FFmpeg command to generate test pattern
        # Using testsrc2 for a moving test pattern that creates transcoding work
        ffmpeg_cmd = [
            "ffmpeg",
            "-re",  # Real-time encoding
            "-f", "lavfi",
            "-i", f"{self.test_pattern}=size=640x360:rate=30",  # Test pattern
            "-f", "lavfi", 
            "-i", "sine=frequency=1000:sample_rate=48000",  # Audio tone
            "-c:v", "libx264",  # H.264 video codec
            "-preset", "ultrafast",  # Fast encoding
            "-tune", "zerolatency",  # Low latency
            "-c:a", "aac",  # AAC audio codec
            "-b:a", "128k",  # Audio bitrate
            "-ar", "48000",  # Audio sample rate
            "-f", "flv",  # FLV format for RTMP
            f"{self.gateway_rtmp}/{stream_key}",  # Destination
            "-t", str(self.stream_duration)  # Duration
        ]
        
        try:
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Stream completed successfully for key: {stream_key}")
                return True
            else:
                logger.error(f"Stream failed with code {process.returncode}")
                logger.error(f"Error: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to generate stream: {e}")
            return False
    
    async def check_stream_processing(self, stream_key: str) -> Dict[str, Any]:
        """Check if stream was processed by orchestrator"""
        try:
            async with httpx.AsyncClient() as client:
                # Check for stream manifest
                response = await client.get(f"{self.gateway_http}/stream/{stream_key}.m3u8")
                if response.status_code == 200:
                    logger.info(f"Stream {stream_key} was transcoded successfully")
                    return {"processed": True, "manifest": True}
                else:
                    logger.warning(f"Stream {stream_key} manifest not found")
                    return {"processed": False, "manifest": False}
        except Exception as e:
            logger.error(f"Failed to check stream processing: {e}")
            return {"processed": False, "error": str(e)}
    
    async def trigger_payment_cycle(self):
        """Run a complete payment trigger cycle"""
        logger.info("=" * 60)
        logger.info("PAYMENT TRIGGER CYCLE")
        logger.info("=" * 60)
        
        # Check orchestrator availability
        orch_status = await self.check_orchestrator_status()
        if not orch_status["available"]:
            logger.warning("No orchestrators available, skipping stream")
            return False
        
        # Generate unique stream key
        stream_key = f"payment_test_{int(time.time())}"
        logger.info(f"Generating stream with key: {stream_key}")
        
        # Send test stream
        success = await self.generate_test_stream(stream_key)
        if not success:
            logger.error("Stream generation failed")
            return False
        
        # Wait a bit for processing
        await asyncio.sleep(5)
        
        # Check if stream was processed
        processing = await self.check_stream_processing(stream_key)
        if processing["processed"]:
            logger.info("✅ Stream processed - payment tickets should be generated")
            return True
        else:
            logger.warning("⚠️ Stream not processed - no payment tickets")
            return False
    
    async def run(self):
        """Main run loop"""
        logger.info("Stream Generator Service Starting")
        logger.info(f"Gateway RTMP: {self.gateway_rtmp}")
        logger.info(f"Stream Duration: {self.stream_duration}s")
        logger.info(f"Stream Interval: {self.stream_interval}s")
        
        cycle = 0
        while True:
            cycle += 1
            logger.info(f"\n--- Stream Cycle {cycle} ---")
            
            try:
                success = await self.trigger_payment_cycle()
                if success:
                    logger.info("Payment cycle completed successfully")
                else:
                    logger.warning("Payment cycle had issues")
                    
            except Exception as e:
                logger.error(f"Error in payment cycle: {e}")
            
            # Wait for next cycle
            logger.info(f"Waiting {self.stream_interval}s until next cycle...")
            await asyncio.sleep(self.stream_interval)


async def main():
    """Main entry point"""
    generator = StreamGenerator()
    
    # Handle shutdown
    import signal
    
    def shutdown_handler(sig, frame):
        logger.info("Shutdown signal received")
        exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    try:
        await generator.run()
    except Exception as e:
        logger.error(f"Service error: {e}")


if __name__ == "__main__":
    # Check if FFmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("FFmpeg is available")
    except:
        logger.error("FFmpeg is not installed! Please install FFmpeg first.")
        exit(1)
    
    asyncio.run(main())