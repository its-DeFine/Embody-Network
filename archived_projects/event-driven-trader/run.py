#!/usr/bin/env python3
"""
Main entry point for the Event-Driven Trading System.
Simple, clean startup with proper logging and error handling.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.event_loop import EventLoop


# Configure logging
def setup_logging(level: str = "INFO"):
    """Configure logging for the entire application"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


async def main():
    """Main application entry point"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║   Event-Driven Adaptive Trading System    ║
    ║                                           ║
    ║   Clean, modular, event-based trading     ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # Setup logging
    setup_logging("INFO")
    logger = logging.getLogger(__name__)
    
    # Create and run event loop
    event_loop = None
    try:
        logger.info("Starting Event-Driven Trading System...")
        
        # Create event loop
        event_loop = EventLoop("config.yaml")
        
        # Setup graceful shutdown
        def shutdown_handler(signum, frame):
            logger.info("Shutdown signal received")
            if event_loop:
                event_loop.running = False
        
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        
        # Run the event loop
        await event_loop.run()
        
    except FileNotFoundError:
        logger.error("config.yaml not found. Please create it from config.example.yaml")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("System shutdown complete")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())