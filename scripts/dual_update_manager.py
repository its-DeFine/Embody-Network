#!/usr/bin/env python3
"""
Dual-Mode Update Manager for Orchestrator Clusters
Intelligently routes updates through Watchtower (image-only) or Full Revamp (structural changes)
"""

import os
import sys
import json
import subprocess
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import yaml
import logging
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UpdateType(Enum):
    """Types of updates that can be detected"""
    IMAGE_ONLY = "image_only"
    STRUCTURAL = "structural"
    MIXED = "mixed"
    NONE = "none"


class UpdateDetector:
    """Detects the type of update needed based on changes"""
    
    def __init__(self, repo_path: str, submodule_path: str = "autonomy"):
        self.repo_path = Path(repo_path)
        self.submodule_path = self.repo_path / submodule_path
        self.compose_files = self._find_compose_files()
        
    def _find_compose_files(self) -> List[Path]:
        """Find all docker-compose files"""
        patterns = ["docker-compose.yml", "docker-compose.*.yml"]
        files = []
        for pattern in patterns:
            files.extend(self.submodule_path.glob(pattern))
        return files
    
    def _get_compose_hash(self, file_path: Path) -> str:
        """Get hash of docker-compose structure (excluding image tags)"""
        with open(file_path, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        # Remove image tags for structural comparison
        if 'services' in compose_data:
            for service in compose_data['services'].values():
                if 'image' in service:
                    # Keep image name but remove tag
                    image = service['image'].split(':')[0]
                    service['image'] = image
        
        # Create deterministic JSON string
        structure_json = json.dumps(compose_data, sort_keys=True)
        return hashlib.sha256(structure_json.encode()).hexdigest()
    
    def detect_changes(self, force_rebuild_on_vtuber_update: bool = False) -> Tuple[UpdateType, Dict]:
        """Detect what type of changes have occurred"""
        logger.info("Detecting update changes...")
        
        # Check for Unreal VTuber submodule updates first
        vtuber_updated = False
        
        # Fetch latest changes
        try:
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(self.repo_path),  # Convert Path to string
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git fetch failed: {e.stderr}")
            # Continue anyway - we might be in a detached state
        
        # Check for submodule updates
        try:
            # Check submodule status first
            submodule_status = subprocess.run(
                ["git", "submodule", "status"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True
            )
            
            # Update submodules
            subprocess.run(
                ["git", "submodule", "update", "--remote"],
                cwd=str(self.repo_path),  # Convert Path to string
                check=False,  # Don't fail on this
                capture_output=True,
                text=True
            )
            
            # Check if docker-vtuber submodule has updates
            if self.submodule_path.exists():
                vtuber_check = subprocess.run(
                    ["git", "diff", "HEAD", "--", "docker-vtuber"],
                    cwd=str(self.submodule_path.parent),
                    capture_output=True,
                    text=True
                )
                if vtuber_check.stdout:
                    vtuber_updated = True
                    logger.info("Unreal VTuber submodule has updates")
                    
        except subprocess.CalledProcessError as e:
            logger.warning(f"Submodule update failed: {e.stderr}")
        
        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "origin/main"],
            cwd=str(self.repo_path),  # Convert Path to string
            capture_output=True,
            text=True
        )
        
        changed_files = result.stdout.strip().split('\n') if result.stdout else []
        
        # Analyze changes
        changes = {
            'compose_changed': False,
            'dockerfile_changed': False,
            'config_changed': False,
            'code_changed': False,
            'vtuber_updated': vtuber_updated,
            'image_only': True,
            'services_added': [],
            'services_removed': [],
            'services_modified': []
        }
        
        for file in changed_files:
            if 'docker-compose' in file:
                changes['compose_changed'] = True
                changes['image_only'] = False
                # Detailed compose analysis
                self._analyze_compose_changes(changes)
            elif 'Dockerfile' in file:
                changes['dockerfile_changed'] = True
            elif file.endswith(('.yaml', '.yml', '.env', '.conf')):
                changes['config_changed'] = True
                changes['image_only'] = False
            elif file.endswith(('.py', '.js', '.go')):
                changes['code_changed'] = True
            # Check if it's a VTuber-related file
            if 'docker-vtuber' in file or 'vtuber' in file.lower():
                vtuber_updated = True
                changes['vtuber_updated'] = True
        
        # Force structural rebuild if VTuber was updated and flag is set
        if force_rebuild_on_vtuber_update and vtuber_updated:
            logger.info("Forcing structural rebuild due to Unreal VTuber updates")
            changes['image_only'] = False
            return UpdateType.STRUCTURAL, changes
        
        # Determine update type
        if not any([changes['compose_changed'], changes['dockerfile_changed'], 
                   changes['config_changed'], changes['code_changed'], vtuber_updated]):
            return UpdateType.NONE, changes
        elif changes['image_only']:
            return UpdateType.IMAGE_ONLY, changes
        elif changes['compose_changed'] or vtuber_updated:
            return UpdateType.STRUCTURAL, changes
        else:
            return UpdateType.MIXED, changes
    
    def _analyze_compose_changes(self, changes: Dict):
        """Analyze specific docker-compose changes"""
        for compose_file in self.compose_files:
            try:
                # Get current version
                with open(compose_file, 'r') as f:
                    current = yaml.safe_load(f)
                
                # Get previous version from git
                result = subprocess.run(
                    ["git", "show", f"HEAD:{compose_file.relative_to(self.repo_path)}"],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    previous = yaml.safe_load(result.stdout)
                    
                    # Compare services
                    current_services = set(current.get('services', {}).keys())
                    previous_services = set(previous.get('services', {}).keys())
                    
                    changes['services_added'].extend(current_services - previous_services)
                    changes['services_removed'].extend(previous_services - current_services)
                    
                    # Check for structural modifications
                    for service in current_services & previous_services:
                        curr_svc = current['services'][service]
                        prev_svc = previous['services'][service]
                        
                        # Check for structural changes (not just image updates)
                        structural_keys = ['ports', 'volumes', 'networks', 'depends_on', 
                                         'environment', 'command', 'entrypoint']
                        
                        for key in structural_keys:
                            if curr_svc.get(key) != prev_svc.get(key):
                                changes['services_modified'].append(service)
                                changes['image_only'] = False
                                break
                                
            except Exception as e:
                logger.warning(f"Failed to analyze {compose_file}: {e}")


class GitHubIntegration:
    """Handles GitHub issue and PR creation"""
    
    def __init__(self, main_repo: str, submodule_repo: str):
        self.main_repo = main_repo
        self.submodule_repo = submodule_repo
        
    def create_issue(self, repo: str, title: str, body: str, labels: List[str] = None) -> str:
        """Create a GitHub issue"""
        cmd = [
            "gh", "issue", "create",
            "--repo", repo,
            "--title", title,
            "--body", body
        ]
        
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            issue_url = result.stdout.strip()
            logger.info(f"Created issue: {issue_url}")
            return issue_url
        else:
            logger.error(f"Failed to create issue: {result.stderr}")
            return ""
    
    def create_pr(self, repo: str, branch: str, title: str, body: str, 
                  issue_url: str = None) -> str:
        """Create a pull request"""
        if issue_url:
            body += f"\n\nCloses {issue_url}"
        
        cmd = [
            "gh", "pr", "create",
            "--repo", repo,
            "--head", branch,
            "--title", title,
            "--body", body
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            pr_url = result.stdout.strip()
            logger.info(f"Created PR: {pr_url}")
            return pr_url
        else:
            logger.error(f"Failed to create PR: {result.stderr}")
            return ""
    
    def create_update_workflow(self, update_type: UpdateType, changes: Dict) -> Dict[str, str]:
        """Create issues and PRs for the update"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"auto-update/{update_type.value}-{timestamp}"
        
        # Prepare issue content
        issue_title = f"[Auto-Update] {update_type.value.replace('_', ' ').title()} Changes Detected"
        
        issue_body = f"""
## Update Type: {update_type.value}

### Changes Detected:
- Docker Compose Changed: {changes.get('compose_changed', False)}
- Dockerfile Changed: {changes.get('dockerfile_changed', False)}
- Configuration Changed: {changes.get('config_changed', False)}
- Code Changed: {changes.get('code_changed', False)}

### Service Changes:
- **Added Services**: {', '.join(changes.get('services_added', [])) or 'None'}
- **Removed Services**: {', '.join(changes.get('services_removed', [])) or 'None'}
- **Modified Services**: {', '.join(changes.get('services_modified', [])) or 'None'}

### Update Strategy:
"""
        
        if update_type == UpdateType.IMAGE_ONLY:
            issue_body += "- Watchtower will handle image updates automatically\n"
            issue_body += "- No structural changes required\n"
        elif update_type == UpdateType.STRUCTURAL:
            issue_body += "- Full cluster revamp required\n"
            issue_body += "- Services will be stopped and recreated\n"
            issue_body += "- Configuration and volume backups recommended\n"
        
        issue_body += f"\n### Automated by Dual-Mode Update System\nTimestamp: {datetime.now().isoformat()}"
        
        # Create issues
        urls = {}
        
        # Main repository issue
        if changes.get('compose_changed') or changes.get('config_changed'):
            urls['main_issue'] = self.create_issue(
                self.main_repo,
                issue_title,
                issue_body,
                ["enhancement", "auto-update"]
            )
        
        # Submodule repository issue if code changed
        if changes.get('code_changed') or changes.get('dockerfile_changed'):
            urls['submodule_issue'] = self.create_issue(
                self.submodule_repo,
                issue_title,
                issue_body,
                ["enhancement", "auto-update"]
            )
        
        # Create PRs if issues were created
        if urls.get('main_issue'):
            pr_title = f"feat: Apply {update_type.value} updates"
            pr_body = f"""
## Summary
Automated update applying {update_type.value} changes detected by the Dual-Mode Update System.

## Changes
{issue_body}

## Testing
- [ ] All services start successfully
- [ ] Health checks pass
- [ ] No breaking changes for existing deployments
"""
            
            urls['main_pr'] = self.create_pr(
                self.main_repo,
                branch_name,
                pr_title,
                pr_body,
                urls['main_issue']
            )
        
        if urls.get('submodule_issue'):
            urls['submodule_pr'] = self.create_pr(
                self.submodule_repo,
                branch_name,
                pr_title,
                pr_body,
                urls['submodule_issue']
            )
        
        return urls


class UpdateOrchestrator:
    """Orchestrates the update process"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.detector = UpdateDetector(repo_path)
        self.github = GitHubIntegration(
            "its-DeFine/Embody-Network",
            "its-DeFine/Unreal_Vtuber"
        )
        self.backup_dir = self.repo_path / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def execute_update(self, update_type: UpdateType, changes: Dict, force_rebuild: bool = False) -> bool:
        """Execute the appropriate update strategy"""
        logger.info(f"Executing {update_type.value} update...")
        
        if update_type == UpdateType.NONE:
            logger.info("No updates needed")
            return True
        
        # Create backup
        self._create_backup()
        
        try:
            if update_type == UpdateType.IMAGE_ONLY and not force_rebuild:
                return self._execute_watchtower_update()
            elif update_type in [UpdateType.STRUCTURAL, UpdateType.MIXED] or force_rebuild:
                # Force rebuild if VTuber was updated
                force_fresh_build = force_rebuild or changes.get('vtuber_updated', False)
                return self._execute_full_revamp(force_rebuild=force_fresh_build)
            else:
                logger.error(f"Unknown update type: {update_type}")
                return False
        except Exception as e:
            logger.error(f"Update failed: {e}")
            self._rollback()
            return False
    
    def _create_backup(self):
        """Create backup of current configuration"""
        logger.info(f"Creating backup at {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup docker-compose files
        for compose_file in self.detector.compose_files:
            shutil.copy2(compose_file, self.backup_dir / compose_file.name)
        
        # Backup environment files
        env_files = self.detector.submodule_path.glob(".env*")
        for env_file in env_files:
            shutil.copy2(env_file, self.backup_dir / env_file.name)
        
        # Save running container state
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        
        with open(self.backup_dir / "running_containers.json", 'w') as f:
            f.write(result.stdout)
    
    def _execute_watchtower_update(self) -> bool:
        """Trigger Watchtower to update images"""
        logger.info("Triggering Watchtower update...")
        
        # Send signal to Watchtower to check for updates immediately
        result = subprocess.run(
            ["docker", "exec", "watchtower_orchestrator", "sh", "-c", "kill -USR1 1"],
            capture_output=True
        )
        
        if result.returncode == 0:
            logger.info("Watchtower update triggered successfully")
            return True
        else:
            logger.warning("Failed to trigger Watchtower, trying alternative method...")
            
            # Alternative: Restart Watchtower with immediate check
            subprocess.run(
                ["docker", "restart", "watchtower_orchestrator"],
                check=True
            )
            return True
    
    def _execute_full_revamp(self, force_rebuild: bool = False) -> bool:
        """Execute full cluster revamp for structural changes"""
        logger.info("Executing full cluster revamp...")
        
        compose_path = self.detector.submodule_path / "docker-compose.yml"
        
        # Stop existing containers
        logger.info("Stopping existing containers...")
        subprocess.run(
            ["docker-compose", "-f", str(compose_path), "down"],
            cwd=str(self.detector.submodule_path),
            check=True
        )
        
        # Clean up old images if forcing rebuild
        if force_rebuild:
            logger.info("Cleaning up old images for fresh rebuild...")
            # Remove all containers and images related to the project
            subprocess.run(
                ["docker-compose", "-f", str(compose_path), "down", "--rmi", "local", "-v"],
                cwd=str(self.detector.submodule_path),
                check=False  # Don't fail if nothing to remove
            )
        
        # Pull latest changes
        logger.info("Pulling latest changes...")
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(self.repo_path),
            check=True
        )
        
        subprocess.run(
            ["git", "submodule", "update", "--init", "--recursive"],
            cwd=str(self.repo_path),
            check=True
        )
        
        # Build and start new containers
        if force_rebuild:
            logger.info("Building containers from scratch (no cache)...")
            subprocess.run(
                ["docker-compose", "-f", str(compose_path), "build", "--no-cache"],
                cwd=str(self.detector.submodule_path),
                check=True
            )
        
        logger.info("Starting new containers...")
        subprocess.run(
            ["docker-compose", "-f", str(compose_path), "up", "-d"],
            cwd=str(self.detector.submodule_path),
            check=True
        )
        
        # Wait for services to be healthy
        if self._health_check():
            logger.info("Full revamp completed successfully")
            return True
        else:
            logger.error("Health checks failed after revamp")
            return False
    
    def _health_check(self, timeout: int = 60) -> bool:
        """Check health of critical services"""
        import time
        import requests
        
        services = [
            ("orchestrator", "http://localhost:8082/health"),
            ("neurosync_s1", "http://localhost:5001/health"),
            ("autogen_agent", "http://localhost:8200/health")
        ]
        
        logger.info("Running health checks...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_healthy = True
            
            for service_name, health_url in services:
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✓ {service_name} is healthy")
                    else:
                        logger.warning(f"✗ {service_name} returned status {response.status_code}")
                        all_healthy = False
                except Exception as e:
                    logger.warning(f"✗ {service_name} health check failed: {e}")
                    all_healthy = False
            
            if all_healthy:
                return True
            
            time.sleep(5)
        
        return False
    
    def _rollback(self):
        """Rollback to previous state"""
        logger.warning("Rolling back to previous state...")
        
        if not self.backup_dir.exists():
            logger.error("No backup found, cannot rollback")
            return
        
        # Restore docker-compose files
        for backup_file in self.backup_dir.glob("docker-compose*.yml"):
            target = self.detector.submodule_path / backup_file.name
            shutil.copy2(backup_file, target)
        
        # Restore environment files
        for backup_file in self.backup_dir.glob(".env*"):
            target = self.detector.submodule_path / backup_file.name
            shutil.copy2(backup_file, target)
        
        # Restart services with restored configuration
        compose_path = self.detector.submodule_path / "docker-compose.yml"
        subprocess.run(
            ["docker-compose", "-f", str(compose_path), "down"],
            cwd=str(self.detector.submodule_path)
        )
        subprocess.run(
            ["docker-compose", "-f", str(compose_path), "up", "-d"],
            cwd=str(self.detector.submodule_path)
        )
        
        logger.info("Rollback completed")
    
    def run(self, auto_approve: bool = False, force_rebuild_on_vtuber_update: bool = False):
        """Main execution flow"""
        logger.info("Starting Dual-Mode Update Manager...")
        
        # Check environment variable for forced rebuilds
        force_rebuild = force_rebuild_on_vtuber_update or \
                       os.getenv('FORCE_REBUILD_ON_VTUBER_UPDATE', 'false').lower() == 'true'
        
        # Detect changes
        update_type, changes = self.detector.detect_changes(force_rebuild_on_vtuber_update=force_rebuild)
        
        logger.info(f"Update type detected: {update_type.value}")
        logger.info(f"Changes: {json.dumps(changes, indent=2)}")
        
        if changes.get('vtuber_updated') and force_rebuild:
            logger.info("VTuber updates detected - forcing full cluster rebuild with no cache")
        
        # Create GitHub workflow
        if not auto_approve:
            urls = self.github.create_update_workflow(update_type, changes)
            logger.info(f"GitHub workflow created: {urls}")
            
            # Wait for approval
            response = input("Proceed with update? (y/n): ")
            if response.lower() != 'y':
                logger.info("Update cancelled by user")
                return
        
        # Execute update
        success = self.execute_update(update_type, changes, force_rebuild=force_rebuild)
        
        if success:
            logger.info("Update completed successfully")
            
            # Create success notification
            self._notify_success(update_type, changes)
        else:
            logger.error("Update failed")
            self._notify_failure(update_type, changes)
    
    def _notify_success(self, update_type: UpdateType, changes: Dict):
        """Send success notification"""
        message = f"✓ Update completed successfully\nType: {update_type.value}\nChanges: {len(changes)} items"
        logger.info(message)
        
        # Could add Slack/Discord/email notification here
    
    def _notify_failure(self, update_type: UpdateType, changes: Dict):
        """Send failure notification"""
        message = f"✗ Update failed\nType: {update_type.value}\nCheck logs for details"
        logger.error(message)
        
        # Could add Slack/Discord/email notification here


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dual-Mode Update Manager")
    parser.add_argument(
        "--repo-path",
        default="/home/geo/operation",
        help="Path to the repository"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in automatic mode without approval"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for updates, don't apply them"
    )
    parser.add_argument(
        "--force-rebuild-on-vtuber-update",
        action="store_true",
        help="Force full cluster rebuild when VTuber repository is updated"
    )
    
    args = parser.parse_args()
    
    orchestrator = UpdateOrchestrator(args.repo_path)
    
    if args.check_only:
        force_rebuild = args.force_rebuild_on_vtuber_update or \
                       os.getenv('FORCE_REBUILD_ON_VTUBER_UPDATE', 'false').lower() == 'true'
        update_type, changes = orchestrator.detector.detect_changes(force_rebuild_on_vtuber_update=force_rebuild)
        print(f"Update type: {update_type.value}")
        print(f"Changes: {json.dumps(changes, indent=2)}")
    else:
        orchestrator.run(
            auto_approve=args.auto,
            force_rebuild_on_vtuber_update=args.force_rebuild_on_vtuber_update
        )


if __name__ == "__main__":
    main()