#!/usr/bin/env python3
"""
Auto-register Livepeer orchestrator to central manager on startup
This should be called from docker-compose as part of the orchestrator startup
"""

import os
import sys
import time
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_manager(manager_url, max_retries=30, delay=2):
    """Wait for central manager to be available"""
    for attempt in range(max_retries):
        try:
            resp = requests.get(f"{manager_url}/health", timeout=5)
            if resp.status_code == 200:
                logger.info("Central manager is available")
                return True
        except:
            pass
        
        logger.info(f"Waiting for central manager... ({attempt+1}/{max_retries})")
        time.sleep(delay)
    
    logger.error("Central manager not available after all retries")
    return False

def auto_register():
    """Auto-register this orchestrator to the central manager"""
    
    # Get configuration from environment
    manager_url = os.environ.get("MANAGER_URL", "http://central-manager:8000")
    orchestrator_id = os.environ.get("ORCHESTRATOR_ID", "livepeer-orchestrator-main")
    orchestrator_endpoint = os.environ.get("ORCHESTRATOR_ENDPOINT", "https://livepeer-orchestrator:9995")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@system.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "LivepeerManager2025!Secure")
    
    logger.info(f"Auto-registering orchestrator: {orchestrator_id}")
    logger.info(f"Manager URL: {manager_url}")
    logger.info(f"Orchestrator endpoint: {orchestrator_endpoint}")
    
    # Wait for manager to be available
    if not wait_for_manager(manager_url):
        return False
    
    # Authenticate with the manager
    try:
        auth_resp = requests.post(
            f"{manager_url}/api/v1/auth/login",
            json={"email": admin_email, "password": admin_password},
            timeout=10
        )
        
        if auth_resp.status_code != 200:
            logger.error(f"Authentication failed: {auth_resp.status_code}")
            return False
        
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Authentication successful")
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False
    
    # Check if already registered
    try:
        check_resp = requests.get(
            f"{manager_url}/api/v1/livepeer/orchestrators",
            headers=headers,
            timeout=10
        )
        
        if check_resp.status_code == 200:
            orchestrators = check_resp.json().get("orchestrators", [])
            for orch in orchestrators:
                if orch["orchestrator_id"] == orchestrator_id:
                    logger.info(f"Orchestrator {orchestrator_id} already registered")
                    return True
    except Exception as e:
        logger.warning(f"Could not check existing registration: {e}")
    
    # Register the orchestrator
    orchestrator_data = {
        "orchestrator_id": orchestrator_id,
        "endpoint": orchestrator_endpoint,
        "capabilities": ["agent-net", "byoc", "transcoding"],
        "region": "docker",
        "status": "active",
        "metadata": {
            "type": "livepeer-orchestrator",
            "container": os.environ.get("HOSTNAME", "unknown"),
            "auto_registered": True,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    try:
        reg_resp = requests.post(
            f"{manager_url}/api/v1/livepeer/orchestrators/register",
            json=orchestrator_data,
            headers=headers,
            timeout=10
        )
        
        if reg_resp.status_code == 200:
            logger.info(f"Successfully registered orchestrator: {orchestrator_id}")
            logger.info(f"Endpoint: {orchestrator_endpoint}")
            logger.info(f"Capabilities: {orchestrator_data['capabilities']}")
            return True
        else:
            logger.error(f"Registration failed: {reg_resp.status_code}")
            logger.error(reg_resp.text)
            return False
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return False

def main():
    """Main entry point"""
    max_retries = 3
    
    for attempt in range(max_retries):
        if auto_register():
            logger.info("Auto-registration complete!")
            sys.exit(0)
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying registration... ({attempt+2}/{max_retries})")
            time.sleep(5)
    
    logger.error("Auto-registration failed after all attempts")
    # Don't exit with error - let the container continue
    sys.exit(0)

if __name__ == "__main__":
    main()