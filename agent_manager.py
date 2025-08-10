#!/usr/bin/env python3
"""
Agent Manager - Dynamic agent creation and management for VTuber system
Loads agents from JSON templates and manages their lifecycle
"""
import json
import os
import glob
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

class AgentManager:
    def __init__(self, templates_dir="/home/geo/operation/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"):
        self.templates_dir = templates_dir
        self.manager_url = "http://localhost:8010"
        self.auth_token = None
        self.loaded_agents = {}
        
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
    
    def load_agent_templates(self) -> List[Dict]:
        """Load all agent templates from JSON files"""
        templates = []
        
        # Load character templates
        json_files = glob.glob(os.path.join(self.templates_dir, "*.json"))
        json_files.extend(glob.glob(os.path.join(self.templates_dir, "templates", "*.json")))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    template = json.load(f)
                    template['source_file'] = json_file
                    templates.append(template)
                    print(f"✓ Loaded template: {template.get('name', 'Unknown')} from {os.path.basename(json_file)}")
            except Exception as e:
                print(f"✗ Failed to load {json_file}: {e}")
        
        return templates
    
    def create_agent_from_template(self, template: Dict) -> Dict:
        """Create an agent configuration from a template"""
        agent_config = {
            "agent_id": template.get("id", f"agent_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            "name": template.get("name", "Unnamed Agent"),
            "type": "character",  # character, cognitive, service, etc.
            "status": "initialized",
            "capabilities": [],
            "configuration": {
                "role": template.get("role", ""),
                "personality_traits": template.get("personality_traits", []),
                "communication_style": template.get("communication_style", ""),
                "domain_expertise": template.get("domain_expertise", []),
                "knowledge_areas": template.get("knowledge_areas", []),
                "behavioral_rules": template.get("behavioral_rules", []),
                "visual_identity": template.get("visual_identity", {}),
                "response_patterns": template.get("response_patterns", {}),
                "formality_level": template.get("formality_level", "casual")
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "template_source": template.get("source_file", ""),
                "version": "1.0"
            }
        }
        
        # Determine capabilities based on template
        if template.get("domain_expertise"):
            if "streaming" in str(template.get("domain_expertise")):
                agent_config["capabilities"].append("streaming")
            if "education" in str(template.get("domain_expertise")):
                agent_config["capabilities"].append("education")
            if "trading" in str(template.get("domain_expertise")):
                agent_config["capabilities"].append("trading")
        
        # Add communication capabilities
        agent_config["capabilities"].extend(["speech", "conversation", "personality"])
        
        return agent_config
    
    def deploy_agent(self, agent_config: Dict, target_system: str = "neurosync") -> bool:
        """Deploy an agent to a target system"""
        if not self.auth_token:
            print("✗ Not authenticated. Please authenticate first.")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Map target system to endpoint
        endpoints = {
            "neurosync": "http://localhost:5001",
            "autogen": "http://localhost:8200",
            "orchestrator": "http://localhost:8082"
        }
        
        endpoint = endpoints.get(target_system, endpoints["neurosync"])
        
        # Register agent with manager
        registration = {
            "agent_id": agent_config["agent_id"],
            "name": agent_config["name"],
            "endpoint": endpoint,
            "capabilities": agent_config["capabilities"],
            "metadata": agent_config
        }
        
        response = requests.post(
            f"{self.manager_url}/api/v1/embodiment/agents/register",
            json=registration,
            headers=headers
        )
        
        if response.ok:
            self.loaded_agents[agent_config["agent_id"]] = agent_config
            print(f"✓ Deployed agent: {agent_config['name']} ({agent_config['agent_id']})")
            
            # If deploying to NeuroSync, activate the character
            if target_system == "neurosync" and "character" in agent_config.get("type", ""):
                self._activate_character(agent_config["agent_id"])
            
            return True
        else:
            print(f"✗ Failed to deploy: {response.status_code} - {response.text}")
            return False
    
    def _activate_character(self, character_id: str):
        """Activate a character in NeuroSync"""
        try:
            response = requests.post(
                "http://localhost:5001/character/activate",
                json={"character_id": character_id}
            )
            if response.ok:
                print(f"  ✓ Activated character in NeuroSync")
        except:
            pass
    
    def list_deployed_agents(self) -> List[Dict]:
        """List all deployed agents"""
        if not self.auth_token:
            print("✗ Not authenticated")
            return []
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        response = requests.get(
            f"{self.manager_url}/api/v1/embodiment/agents",
            headers=headers
        )
        
        if response.ok:
            return response.json()
        return []
    
    def create_custom_agent(self, name: str, role: str, traits: List[str], expertise: List[str]) -> Dict:
        """Create a custom agent from scratch"""
        agent_config = {
            "agent_id": f"custom_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "type": "character",
            "status": "initialized",
            "capabilities": ["speech", "conversation", "personality"],
            "configuration": {
                "role": role,
                "personality_traits": traits,
                "communication_style": "adaptive",
                "domain_expertise": expertise,
                "knowledge_areas": expertise,
                "behavioral_rules": [
                    f"Act as a {role}",
                    f"Embody these traits: {', '.join(traits)}",
                    f"Focus on: {', '.join(expertise)}"
                ],
                "formality_level": "professional" if "professional" in role.lower() else "casual"
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "custom_created": True,
                "version": "1.0"
            }
        }
        
        return agent_config

# Example usage
if __name__ == "__main__":
    manager = AgentManager()
    
    print("=" * 60)
    print("AGENT MANAGER - Dynamic Agent System")
    print("=" * 60)
    print()
    
    # Authenticate
    if manager.authenticate():
        print("✓ Authenticated with Central Manager")
        print()
        
        # Load templates
        print("Loading agent templates...")
        templates = manager.load_agent_templates()
        print(f"\n✓ Found {len(templates)} templates")
        print()
        
        # Create and deploy agents from templates
        print("Creating agents from templates...")
        for template in templates[:3]:  # Deploy first 3 as example
            agent = manager.create_agent_from_template(template)
            manager.deploy_agent(agent, "neurosync")
        
        print()
        
        # Create a custom agent
        print("Creating custom agent...")
        custom = manager.create_custom_agent(
            name="Tech Expert",
            role="Technology Educator",
            traits=["knowledgeable", "patient", "enthusiastic"],
            expertise=["AI", "programming", "web development"]
        )
        manager.deploy_agent(custom, "autogen")
        
        print()
        
        # List all agents
        print("Currently deployed agents:")
        agents = manager.list_deployed_agents()
        for agent in agents:
            print(f"  - {agent['name']} ({agent['agent_id']})")
            print(f"    Type: {agent.get('metadata', {}).get('type', 'unknown')}")
            print(f"    Status: {agent['status']}")
    else:
        print("✗ Authentication failed")