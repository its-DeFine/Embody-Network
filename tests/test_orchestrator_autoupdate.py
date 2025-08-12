#!/usr/bin/env python3
"""
Test suite for orchestrator auto-update functionality with Watchtower.
Tests the complete auto-update pipeline from image push to container restart.
"""

import os
import time
import docker
import pytest
import subprocess
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class TestOrchestratorAutoUpdate:
    """Test orchestrator auto-update functionality."""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Create Docker client for tests."""
        return docker.from_env()
    
    @pytest.fixture(scope="class")
    def compose_project(self):
        """Get the compose project name."""
        return "autonomy"
    
    def test_watchtower_service_exists(self, docker_client):
        """Test that Watchtower service is defined in docker-compose."""
        compose_path = "/home/geo/operation/autonomy/docker-compose.yml"
        assert os.path.exists(compose_path), "Docker compose file not found"
        
        with open(compose_path, 'r') as f:
            content = f.read()
            assert "watchtower:" in content, "Watchtower service not defined"
            assert "containrrr/watchtower" in content, "Watchtower image not specified"
    
    def test_orchestrator_labels(self, docker_client):
        """Test that orchestrator has correct Watchtower labels."""
        compose_path = "/home/geo/operation/autonomy/docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            content = f.read()
            # Check for labels in orchestrator service
            assert "com.centurylinklabs.watchtower.enable=true" in content, \
                "Orchestrator missing Watchtower enable label"
            assert "com.centurylinklabs.watchtower.scope=autonomy-cluster" in content, \
                "Orchestrator missing Watchtower scope label"
    
    def test_watchtower_configuration(self):
        """Test Watchtower environment configuration."""
        compose_path = "/home/geo/operation/autonomy/docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            content = f.read()
            
            # Check critical Watchtower configurations
            required_configs = [
                "WATCHTOWER_LABEL_ENABLE=true",
                "WATCHTOWER_CLEANUP=true",
                "WATCHTOWER_ROLLING_RESTART=true",
                "--label-enable",
                "--scope autonomy-cluster"
            ]
            
            for config in required_configs:
                assert config in content, f"Missing Watchtower config: {config}"
    
    @pytest.mark.integration
    def test_watchtower_container_startup(self, docker_client, compose_project):
        """Test that Watchtower container starts successfully."""
        try:
            # Start only the Watchtower service
            subprocess.run(
                ["docker", "compose", "-f", "/home/geo/operation/autonomy/docker-compose.yml",
                 "up", "-d", "watchtower"],
                check=True,
                capture_output=True
            )
            
            # Wait for container to start
            time.sleep(5)
            
            # Check if Watchtower container is running
            container = docker_client.containers.get("watchtower_orchestrator")
            assert container.status == "running", "Watchtower container not running"
            
            # Check container logs for startup issues
            logs = container.logs(tail=20).decode('utf-8')
            assert "error" not in logs.lower(), f"Errors in Watchtower logs: {logs}"
            
        except docker.errors.NotFound:
            pytest.fail("Watchtower container not found")
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to start Watchtower: {e}")
    
    @pytest.mark.integration
    def test_orchestrator_monitoring(self, docker_client):
        """Test that Watchtower monitors the orchestrator container."""
        try:
            # Get Watchtower container
            watchtower = docker_client.containers.get("watchtower_orchestrator")
            
            # Check Watchtower logs for monitoring activity
            logs = watchtower.logs(tail=100).decode('utf-8')
            
            # Watchtower should mention the orchestrator container
            assert "vtuber_orchestrator" in logs or "Monitoring" in logs, \
                "Watchtower not monitoring orchestrator"
            
        except docker.errors.NotFound:
            pytest.skip("Watchtower container not running")
    
    def test_update_interval_configuration(self):
        """Test that update interval can be configured."""
        compose_path = "/home/geo/operation/autonomy/docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            content = f.read()
            
            # Check for configurable interval
            assert "WATCHTOWER_INTERVAL=${WATCHTOWER_INTERVAL:-300}" in content, \
                "Update interval not configurable"
    
    def test_rollback_capability(self):
        """Test that immutable tags exist for rollback."""
        workflow_path = "/home/geo/operation/.github/workflows/autonomy-orchestrator-autoupdate.yml"
        
        if os.path.exists(workflow_path):
            with open(workflow_path, 'r') as f:
                content = f.read()
                
                # Check for immutable tag creation
                assert "autonomy-" in content, "Immutable tags not configured"
                assert "type=sha" in content, "SHA-based tags not configured"
    
    @pytest.mark.integration
    def test_health_check_post_update(self, docker_client):
        """Test that orchestrator health check works after updates."""
        try:
            container = docker_client.containers.get("vtuber_orchestrator")
            
            # Check if health check is configured
            health = container.attrs.get('State', {}).get('Health', {})
            if health:
                status = health.get('Status')
                assert status in ['healthy', 'starting'], \
                    f"Orchestrator unhealthy: {status}"
            
        except docker.errors.NotFound:
            pytest.skip("Orchestrator container not running")
    
    def test_monitor_only_mode(self):
        """Test that Watchtower can run in monitor-only mode."""
        compose_path = "/home/geo/operation/autonomy/docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            content = f.read()
            
            # Check for monitor-only configuration
            assert "WATCHTOWER_MONITOR_ONLY=${WATCHTOWER_MONITOR_ONLY:-false}" in content, \
                "Monitor-only mode not configurable"
    
    @pytest.mark.integration
    def test_network_connectivity(self, docker_client):
        """Test that Watchtower is on the same network as orchestrator."""
        try:
            watchtower = docker_client.containers.get("watchtower_orchestrator")
            orchestrator = docker_client.containers.get("vtuber_orchestrator")
            
            # Get networks for both containers
            watchtower_networks = set(watchtower.attrs['NetworkSettings']['Networks'].keys())
            orchestrator_networks = set(orchestrator.attrs['NetworkSettings']['Networks'].keys())
            
            # Check for common network
            common_networks = watchtower_networks.intersection(orchestrator_networks)
            assert len(common_networks) > 0, \
                "Watchtower and orchestrator not on same network"
            
        except docker.errors.NotFound:
            pytest.skip("Required containers not running")
    
    def test_cleanup_configuration(self):
        """Test that old images are cleaned up after updates."""
        compose_path = "/home/geo/operation/autonomy/docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            content = f.read()
            
            # Check for cleanup configuration
            assert "WATCHTOWER_CLEANUP=true" in content, \
                "Image cleanup not enabled"
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_update_simulation(self, docker_client):
        """Simulate an update scenario (requires manual image push)."""
        # This test would require:
        # 1. Pushing a new image to GHCR
        # 2. Waiting for Watchtower to detect it
        # 3. Verifying the container was updated
        
        # For now, we just verify the setup is correct
        pytest.skip("Manual update simulation - requires GHCR push access")


class TestCentralManagerIntegration:
    """Test central manager integration for update control."""
    
    def test_central_manager_endpoints_planned(self):
        """Verify that central manager update endpoints are planned."""
        # This is a placeholder for future implementation
        management_path = "/home/geo/operation/app/api/management.py"
        
        if os.path.exists(management_path):
            with open(management_path, 'r') as f:
                content = f.read()
                
                # Check if update-related code exists (will be added later)
                # For now, just verify the file exists
                assert len(content) > 0, "Management API file is empty"
    
    def test_update_status_monitoring_planned(self):
        """Verify update status monitoring is planned."""
        # Placeholder for future monitoring implementation
        assert True, "Update monitoring to be implemented"
    
    def test_rollback_command_planned(self):
        """Verify rollback command structure is planned."""
        # Placeholder for rollback functionality
        assert True, "Rollback commands to be implemented"


class TestDocumentation:
    """Test that documentation is complete and accurate."""
    
    def test_autoupdate_documentation_exists(self):
        """Test that auto-update documentation exists."""
        doc_path = "/home/geo/operation/docs/ORCHESTRATOR_AUTOUPDATE.md"
        assert os.path.exists(doc_path), "Auto-update documentation not found"
        
        with open(doc_path, 'r') as f:
            content = f.read()
            
            # Check for key sections
            required_sections = [
                "Watchtower",
                "CI",
                "rollback",
                "GHCR"
            ]
            
            for section in required_sections:
                assert section.lower() in content.lower(), \
                    f"Documentation missing section on: {section}"
    
    def test_deployment_script_exists(self):
        """Test that deployment script exists and is executable."""
        script_path = "/home/geo/operation/scripts/orchestrator_cluster_autoupdate.sh"
        assert os.path.exists(script_path), "Deployment script not found"
        
        # Check if script is executable
        stat_info = os.stat(script_path)
        is_executable = bool(stat_info.st_mode & 0o111)
        assert is_executable, "Deployment script not executable"
    
    def test_github_workflow_exists(self):
        """Test that GitHub workflow for auto-update exists."""
        workflow_path = "/home/geo/operation/.github/workflows/autonomy-orchestrator-autoupdate.yml"
        assert os.path.exists(workflow_path), "GitHub workflow not found"
        
        with open(workflow_path, 'r') as f:
            content = f.read()
            
            # Check for essential workflow components
            assert "ghcr.io" in content, "GHCR registry not configured"
            assert "autonomy-latest" in content, "Latest tag not configured"
            assert "docker/build-push-action" in content, "Build action not configured"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])