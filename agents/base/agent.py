import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import autogen
from autogen.agentchat import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import httpx

# Import shared modules
import sys
sys.path.append('/app')
from shared.models.agent_models import AgentType
from shared.events.event_types import Event, EventType
from shared.utils.message_queue import get_message_queue

# Import agent type implementations
from agent_types.trading_agent import TradingAgent
from agent_types.analysis_agent import AnalysisAgent
from agent_types.risk_agent import RiskManagementAgent
from agent_types.portfolio_agent import PortfolioOptimizationAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomerAgent:
    """Base class for customer AutoGen agents"""
    
    def __init__(self):
        self.agent_id = os.getenv("AGENT_ID")
        self.customer_id = os.getenv("CUSTOMER_ID")
        self.agent_type = AgentType(os.getenv("AGENT_TYPE", "trading"))
        self.agent_name = os.getenv("AGENT_NAME", "Agent")
        
        # Parse configurations
        self.config = json.loads(os.getenv("CONFIG", "{}"))
        self.autogen_config = json.loads(os.getenv("AUTOGEN_CONFIG", "{}"))
        
        # AutoGen components
        self.assistant_agent: Optional[AssistantAgent] = None
        self.user_proxy: Optional[UserProxyAgent] = None
        self.group_chat: Optional[GroupChat] = None
        self.manager: Optional[GroupChatManager] = None
        self.team_agents: List[AssistantAgent] = []
        
        # Message queue
        self.mq = None
        self.running = True
        
        # OpenBB client
        self.openbb_client: Optional[httpx.AsyncClient] = None
        self.openbb_base_url = os.getenv("OPENBB_SERVICE_URL", "http://openbb-adapter:8003")
        
        logger.info(f"Initializing {self.agent_type} agent: {self.agent_id}")
    
    async def initialize(self):
        """Initialize the agent"""
        # Connect to message queue
        self.mq = await self._connect_message_queue()
        
        # Initialize OpenBB client
        await self._init_openbb_client()
        
        # Setup AutoGen agents
        self._setup_autogen_agents()
        
        # Subscribe to messages
        await self._setup_subscriptions()
        
        # Send heartbeat
        asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Agent {self.agent_id} initialized successfully")
    
    async def _connect_message_queue(self):
        """Connect to RabbitMQ"""
        from shared.utils.message_queue import MessageQueue
        mq = MessageQueue(os.getenv("RABBITMQ_URL", "amqp://admin:password@rabbitmq:5672/"))
        await mq.connect()
        return mq
    
    async def _init_openbb_client(self):
        """Initialize OpenBB HTTP client"""
        self.openbb_client = httpx.AsyncClient(
            base_url=self.openbb_base_url,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Test connection
        try:
            response = await self.openbb_client.get("/health")
            if response.status_code == 200:
                logger.info("Connected to OpenBB adapter service")
            else:
                logger.warning(f"OpenBB adapter health check returned {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenBB adapter: {e}")
            # Continue without OpenBB if not available
            self.openbb_client = None
    
    async def get_market_data(self, symbol: str, interval: str = "1d", start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get market data from OpenBB service"""
        if not self.openbb_client:
            logger.warning("OpenBB client not initialized")
            return {"error": "OpenBB service not available"}
        
        try:
            params = {
                "symbol": symbol,
                "interval": interval
            }
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = await self.openbb_client.get("/api/v1/market/data", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return {"error": str(e)}
    
    async def get_technical_analysis(self, symbol: str, indicators: List[str]) -> Dict[str, Any]:
        """Get technical analysis from OpenBB service"""
        if not self.openbb_client:
            logger.warning("OpenBB client not initialized")
            return {"error": "OpenBB service not available"}
        
        try:
            response = await self.openbb_client.post(
                "/api/v1/analysis/technical",
                json={"symbol": symbol, "indicators": indicators}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching technical analysis: {e}")
            return {"error": str(e)}
    
    async def analyze_portfolio(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze portfolio using OpenBB service"""
        if not self.openbb_client:
            logger.warning("OpenBB client not initialized")
            return {"error": "OpenBB service not available"}
        
        try:
            response = await self.openbb_client.post(
                "/api/v1/portfolio/analyze",
                json={"positions": positions}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return {"error": str(e)}
    
    def _setup_autogen_agents(self):
        """Setup AutoGen agents based on agent type"""
        # LLM configuration
        llm_config = {
            "config_list": self._get_llm_config_list(),
            "temperature": self.autogen_config.get("temperature", 0.7),
            "max_tokens": self.autogen_config.get("max_tokens", 1000),
            "timeout": 120
        }
        
        # Create type-specific agent
        if self.agent_type == AgentType.TRADING:
            agent_impl = TradingAgent(self.config, self.openbb_client)
        elif self.agent_type == AgentType.ANALYSIS:
            agent_impl = AnalysisAgent(self.config)
        elif self.agent_type == AgentType.RISK_MANAGEMENT:
            agent_impl = RiskManagementAgent(self.config)
        elif self.agent_type == AgentType.PORTFOLIO_OPTIMIZATION:
            agent_impl = PortfolioOptimizationAgent(self.config)
        else:
            # Custom agent type
            agent_impl = None
        
        # Create assistant agent
        self.assistant_agent = AssistantAgent(
            name=self.agent_name,
            llm_config=llm_config,
            system_message=agent_impl.get_system_message() if agent_impl else self.autogen_config.get("system_message", ""),
            max_consecutive_auto_reply=self.autogen_config.get("max_consecutive_auto_reply", 10)
        )
        
        # Create user proxy agent
        self.user_proxy = UserProxyAgent(
            name=f"{self.agent_name}_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config={
                "work_dir": f"/tmp/agent_{self.agent_id}",
                "use_docker": False
            }
        )
        
        # Register custom functions if available
        if agent_impl:
            for func_name, func in agent_impl.get_functions().items():
                self.user_proxy.register_function(
                    function_map={func_name: func}
                )
    
    def _get_llm_config_list(self) -> List[Dict[str, Any]]:
        """Get LLM configuration list"""
        config_list = []
        
        # OpenAI configuration
        if os.getenv("OPENAI_API_KEY"):
            config_list.append({
                "model": self.autogen_config.get("openai_model", "gpt-4-turbo-preview"),
                "api_key": os.getenv("OPENAI_API_KEY")
            })
        
        # Anthropic configuration
        if os.getenv("ANTHROPIC_API_KEY"):
            config_list.append({
                "model": self.autogen_config.get("anthropic_model", "claude-3-opus-20240229"),
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "api_type": "anthropic"
            })
        
        # Custom model configuration
        if "custom_models" in self.autogen_config:
            config_list.extend(self.autogen_config["custom_models"])
        
        return config_list
    
    async def _setup_subscriptions(self):
        """Setup message queue subscriptions"""
        # Subscribe to direct messages
        await self.mq.receive_direct_messages(
            f"agent-{self.agent_id}",
            self._handle_direct_message
        )
        
        # Subscribe to team messages if part of a team
        if self.config.get("team_id"):
            await self.mq.receive_broadcasts(
                f"team-{self.config['team_id']}",
                self._handle_team_message
            )
    
    async def _handle_direct_message(self, message: Dict[str, Any]):
        """Handle direct messages"""
        try:
            message_type = message.get("message_type")
            payload = message.get("payload", {})
            
            if message_type == "config.update":
                await self._update_config(payload)
            elif message_type == "task.execute":
                await self._execute_task(payload)
            elif message_type == "team.join":
                await self._join_team(payload)
            elif message_type == "conversation.start":
                await self._start_conversation(payload)
            
        except Exception as e:
            logger.error(f"Error handling direct message: {e}")
    
    async def _handle_team_message(self, message: Dict[str, Any]):
        """Handle team broadcast messages"""
        try:
            message_type = message.get("message_type")
            payload = message.get("payload", {})
            
            if message_type == "team.task":
                await self._handle_team_task(payload)
            elif message_type == "team.sync":
                await self._sync_with_team(payload)
            
        except Exception as e:
            logger.error(f"Error handling team message: {e}")
    
    async def _update_config(self, new_config: Dict[str, Any]):
        """Update agent configuration"""
        self.config.update(new_config)
        
        # Reinitialize agent if needed
        if new_config.get("reinitialize"):
            self._setup_autogen_agents()
        
        logger.info(f"Updated configuration for agent {self.agent_id}")
    
    async def _execute_task(self, task: Dict[str, Any]):
        """Execute a task using AutoGen"""
        try:
            task_id = task.get("task_id")
            task_type = task.get("type")
            parameters = task.get("parameters", {})
            
            # Create task message
            task_message = self._format_task_message(task_type, parameters)
            
            # Execute task
            if self.group_chat and self.manager:
                # Use group chat for team tasks
                self.user_proxy.initiate_chat(
                    self.manager,
                    message=task_message
                )
            else:
                # Direct conversation
                self.user_proxy.initiate_chat(
                    self.assistant_agent,
                    message=task_message
                )
            
            # Get results
            chat_history = self.user_proxy.chat_messages[self.assistant_agent]
            result = chat_history[-1]["content"] if chat_history else "No result"
            
            # Send result event
            await self._send_task_result(task_id, result)
            
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            await self._send_task_error(task.get("task_id"), str(e))
    
    def _format_task_message(self, task_type: str, parameters: Dict[str, Any]) -> str:
        """Format task message for AutoGen"""
        if self.agent_type == AgentType.TRADING:
            if task_type == "analyze_market":
                return f"Analyze the market for {parameters.get('symbol', 'BTC/USDT')} and provide trading signals."
            elif task_type == "execute_trade":
                return f"Execute a {parameters.get('side', 'buy')} order for {parameters.get('amount', 0)} {parameters.get('symbol', 'BTC/USDT')}."
        elif self.agent_type == AgentType.ANALYSIS:
            return f"Perform {task_type} analysis with parameters: {json.dumps(parameters)}"
        elif self.agent_type == AgentType.RISK_MANAGEMENT:
            return f"Evaluate risk for: {json.dumps(parameters)}"
        else:
            return f"Execute {task_type} with parameters: {json.dumps(parameters)}"
    
    async def _join_team(self, team_info: Dict[str, Any]):
        """Join an agent team"""
        team_id = team_info.get("team_id")
        team_members = team_info.get("team_members", [])
        orchestrator_config = team_info.get("orchestrator_config", {})
        
        # Create agents for team members
        self.team_agents = []
        for member_id in team_members:
            if member_id != self.agent_id:
                # Create proxy agent for team member
                member_agent = AssistantAgent(
                    name=f"TeamMember_{member_id}",
                    llm_config=False,  # Proxy agent, no LLM
                    system_message=f"I am agent {member_id}"
                )
                self.team_agents.append(member_agent)
        
        # Create group chat
        all_agents = [self.assistant_agent] + self.team_agents + [self.user_proxy]
        self.group_chat = GroupChat(
            agents=all_agents,
            messages=[],
            max_round=orchestrator_config.get("max_rounds", 10)
        )
        
        # Create group chat manager
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.assistant_agent.llm_config
        )
        
        self.config["team_id"] = team_id
        logger.info(f"Agent {self.agent_id} joined team {team_id}")
    
    async def _start_conversation(self, conversation: Dict[str, Any]):
        """Start a conversation with another agent"""
        target_agent_id = conversation.get("target_agent_id")
        message = conversation.get("message")
        
        # Send message through message queue
        await self.mq.send_direct_message(
            target=f"agent-{target_agent_id}",
            message_type="conversation.message",
            payload={
                "from_agent_id": self.agent_id,
                "message": message
            }
        )
    
    async def _send_task_result(self, task_id: str, result: Any):
        """Send task execution result"""
        event = Event(
            event_id=f"task-result-{task_id}",
            event_type=EventType.MESSAGE_SENT,
            source=f"agent-{self.agent_id}",
            customer_id=self.customer_id,
            data={
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.mq.publish_event(event)
    
    async def _send_task_error(self, task_id: str, error: str):
        """Send task execution error"""
        event = Event(
            event_id=f"task-error-{task_id}",
            event_type=EventType.MESSAGE_FAILED,
            source=f"agent-{self.agent_id}",
            customer_id=self.customer_id,
            data={
                "task_id": task_id,
                "agent_id": self.agent_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.mq.publish_event(event)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                event = Event(
                    event_id=f"heartbeat-{self.agent_id}-{datetime.utcnow().timestamp()}",
                    event_type=EventType.AGENT_HEARTBEAT,
                    source=f"agent-{self.agent_id}",
                    customer_id=self.customer_id,
                    data={
                        "agent_id": self.agent_id,
                        "status": "running",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await self.mq.publish_event(event)
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(30)
    
    async def run(self):
        """Run the agent"""
        await self.initialize()
        
        try:
            # Keep running
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info(f"Shutting down agent {self.agent_id}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        self.running = False
        
        # Close OpenBB client
        if self.openbb_client:
            await self.openbb_client.aclose()
        
        # Disconnect message queue
        if self.mq:
            await self.mq.disconnect()


async def main():
    """Main entry point"""
    agent = CustomerAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())