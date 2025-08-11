#!/usr/bin/env python3
"""
Agent Manager V2 - Proper distinction between Orchestrators, Agents, and Infrastructure
"""
import json
import os
import glob
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

class AgentManagerV2:
    def __init__(self):
        self.manager_url = "http://localhost:8010"
        self.auth_token = None
        self.templates_dir = "/home/geo/operation/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"
        
        # Define what are infrastructure services (not agents)
        self.infrastructure_ids = [
            "neurosync-s1",           # Infrastructure: Avatar system
            "autogen-multi-agent",    # Infrastructure: Cognitive engine
            "scb-gateway",            # Infrastructure: Message router
            "rtmp-streamer",          # Infrastructure: Streaming server
        ]
        
        # Track active agent
        self.active_agent_id = None
        
    def authenticate(self, password=None):
        """Authenticate with central manager"""
        if password is None:
            password = os.environ.get("MANAGER_ADMIN_PASSWORD", "admin")
        response = requests.post(
            f"{self.manager_url}/api/v1/auth/token",
            data={"username": "admin@system.com", "password": password}
        )
        if response.ok:
            self.auth_token = response.json()["access_token"]
            return True
        return False
    
    def get_all_entities(self) -> Dict[str, List]:
        """Get all registered entities and categorize them properly"""
        if not self.auth_token:
            return {"orchestrators": [], "agents": [], "infrastructure": []}
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        response = requests.get(f"{self.manager_url}/api/v1/embodiment/agents", headers=headers)
        
        if not response.ok:
            return {"orchestrators": [], "agents": [], "infrastructure": []}
        
        all_entities = response.json()
        
        orchestrators = []
        agents = []
        infrastructure = []
        
        for entity in all_entities:
            entity_id = entity.get("agent_id", "")
            entity_type = entity.get("metadata", {}).get("type", "")
            
            # Categorize based on ID and type
            if entity_id in self.infrastructure_ids or entity_type in ["streaming_server", "message_broker", "avatar_controller", "cognitive_engine"]:
                infrastructure.append(entity)
            elif "orchestrator" in entity_id.lower() or entity_type == "orchestrator":
                orchestrators.append(entity)
            else:
                # This is an actual agent (character)
                agents.append(entity)
        
        return {
            "orchestrators": orchestrators,
            "agents": agents,
            "infrastructure": infrastructure
        }
    
    def get_active_agent(self) -> Optional[str]:
        """Get the currently active agent from NeuroSync"""
        try:
            response = requests.get("http://localhost:5001/character/current")
            if response.ok:
                data = response.json()
                return data.get("current_character", {}).get("id")
        except:
            pass
        return self.active_agent_id
    
    def set_active_agent(self, agent_id: str) -> bool:
        """Set an agent as active (display it)"""
        try:
            # Try to activate in NeuroSync
            response = requests.post(
                "http://localhost:5001/character/activate",
                json={"character_id": agent_id}
            )
            if response.ok:
                self.active_agent_id = agent_id
                print(f"✓ Activated agent: {agent_id}")
                return True
        except Exception as e:
            print(f"✗ Failed to activate: {e}")
        return False
    
    def register_orchestrator(self, name: str, endpoint: str, manages: List[str]) -> bool:
        """Register a new orchestrator"""
        if not self.auth_token:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        orchestrator_config = {
            "agent_id": f"orchestrator_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "endpoint": endpoint,
            "capabilities": ["orchestration", "coordination", "workflow", "routing"],
            "orchestrator_id": f"{name.lower().replace(' ', '_')}_orch",
            "metadata": {
                "type": "orchestrator",
                "manages": manages,
                "created_at": datetime.now().isoformat(),
                "active": False
            }
        }
        
        response = requests.post(
            f"{self.manager_url}/api/v1/embodiment/agents/register",
            json=orchestrator_config,
            headers=headers
        )
        
        return response.ok
    
    def register_agent(self, template: Dict, activate: bool = False) -> bool:
        """Register an agent (character) - not infrastructure"""
        if not self.auth_token:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        agent_config = {
            "agent_id": template.get("id", f"agent_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            "name": template.get("name", "Unnamed Agent"),
            "endpoint": "http://localhost:5001",  # Agents run on NeuroSync
            "capabilities": ["character", "personality", "speech", "emotion"],
            "metadata": {
                "type": "agent",  # Clear type: agent, not infrastructure
                "character_template": template,
                "active": False,
                "created_at": datetime.now().isoformat()
            }
        }
        
        response = requests.post(
            f"{self.manager_url}/api/v1/embodiment/agents/register",
            json=agent_config,
            headers=headers
        )
        
        if response.ok and activate:
            self.set_active_agent(agent_config["agent_id"])
        
        return response.ok
    
    def get_orchestrator_status(self, orchestrator_id: str) -> Dict:
        """Get detailed status of an orchestrator"""
        try:
            # Check if orchestrator endpoint is reachable
            entities = self.get_all_entities()
            for orch in entities["orchestrators"]:
                if orch["agent_id"] == orchestrator_id:
                    endpoint = orch.get("endpoint", "")
                    if endpoint:
                        # Try to reach health endpoint
                        health_url = f"{endpoint}/health"
                        response = requests.get(health_url, timeout=2)
                        if response.ok:
                            return {
                                "id": orchestrator_id,
                                "name": orch["name"],
                                "status": "active",
                                "health": response.json(),
                                "manages": orch.get("metadata", {}).get("manages", [])
                            }
                    return {
                        "id": orchestrator_id,
                        "name": orch["name"],
                        "status": "registered",
                        "manages": orch.get("metadata", {}).get("manages", [])
                    }
        except:
            pass
        return {"id": orchestrator_id, "status": "unknown"}
    
    def load_agent_templates(self) -> List[Dict]:
        """Load character templates from JSON files"""
        templates = []
        json_files = glob.glob(os.path.join(self.templates_dir, "*.json"))
        json_files.extend(glob.glob(os.path.join(self.templates_dir, "templates", "*.json")))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    template = json.load(f)
                    template['source_file'] = json_file
                    templates.append(template)
            except:
                pass
        
        return templates
    
    def get_summary(self) -> Dict:
        """Get a complete summary of the system state"""
        entities = self.get_all_entities()
        active_agent = self.get_active_agent()
        
        # Check orchestrator statuses
        for orch in entities["orchestrators"]:
            orch["live_status"] = self.get_orchestrator_status(orch["agent_id"])
        
        # Mark active agent
        for agent in entities["agents"]:
            agent["is_active"] = (agent["agent_id"] == active_agent)
        
        return {
            "orchestrators": {
                "total": len(entities["orchestrators"]),
                "active": sum(1 for o in entities["orchestrators"] if o.get("live_status", {}).get("status") == "active"),
                "list": entities["orchestrators"]
            },
            "agents": {
                "total": len(entities["agents"]),
                "active": active_agent,
                "list": entities["agents"]
            },
            "infrastructure": {
                "total": len(entities["infrastructure"]),
                "list": entities["infrastructure"]
            }
        }

# CLI for testing
if __name__ == "__main__":
    manager = AgentManagerV2()
    
    print("=" * 70)
    print("AGENT MANAGER V2 - Proper Entity Classification")
    print("=" * 70)
    
    if manager.authenticate():
        print("✓ Authenticated\n")
        
        summary = manager.get_summary()
        
        print("🎛️  ORCHESTRATORS (Coordination Systems)")
        print("-" * 40)
        print(f"Total: {summary['orchestrators']['total']}")
        print(f"Active: {summary['orchestrators']['active']}")
        for orch in summary['orchestrators']['list']:
            status = orch.get('live_status', {}).get('status', 'unknown')
            print(f"  • {orch['name']} ({orch['agent_id']})")
            print(f"    Status: {status}")
            manages = orch.get('metadata', {}).get('manages', [])
            if manages:
                print(f"    Manages: {', '.join(manages)}")
        
        print("\n🎭 AGENTS (Characters/Personalities)")
        print("-" * 40)
        print(f"Total: {summary['agents']['total']}")
        print(f"Active: {summary['agents']['active'] or 'None'}")
        for agent in summary['agents']['list']:
            active = "✓ ACTIVE" if agent.get('is_active') else ""
            print(f"  • {agent['name']} ({agent['agent_id']}) {active}")
            template = agent.get('metadata', {}).get('character_template', {})
            if template.get('role'):
                print(f"    Role: {template['role']}")
        
        print("\n🔧 INFRASTRUCTURE (Services/Containers)")
        print("-" * 40)
        print(f"Total: {summary['infrastructure']['total']}")
        for infra in summary['infrastructure']['list']:
            print(f"  • {infra['name']} ({infra['agent_id']})")
            print(f"    Type: {infra.get('metadata', {}).get('type', 'service')}")
            print(f"    Status: {infra.get('status', 'unknown')}")
        
        print("\n" + "=" * 70)
        
        # Test loading templates
        print("\n📋 Available Agent Templates:")
        templates = manager.load_agent_templates()
        for t in templates:
            print(f"  • {t.get('name', 'Unknown')} - {t.get('role', 'No role')}")
    else:
        print("✗ Authentication failed")