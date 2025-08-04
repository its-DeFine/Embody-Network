"""Trading Agent Implementation"""
from .base_agent import BaseAgent

class TradingAgent(BaseAgent):
    """Agent for cryptocurrency and stock trading"""
    
    def get_system_message(self) -> str:
        return """You are a professional trading agent specialized in cryptocurrency and stock markets.
        Your responsibilities include:
        - Analyzing market trends and patterns
        - Executing trades based on strategy
        - Managing risk with stop-loss and position sizing
        - Tracking portfolio performance
        
        Always prioritize risk management and never risk more than 2% per trade."""
    
    async def handle_task(self, task: dict):
        """Handle trading-specific tasks"""
        task_type = task.get("type")
        
        if task_type == "analyze_market":
            symbol = task.get("symbol", "BTC/USD")
            await self.analyze_market(symbol)
            
        elif task_type == "execute_trade":
            await self.execute_trade(task)
            
        else:
            await super().handle_task(task)
    
    async def analyze_market(self, symbol: str):
        """Analyze market for trading opportunities"""
        market_data = await self.get_market_data(symbol)
        
        # Use AutoGen to analyze
        message = f"""Analyze the following market data for {symbol} and provide trading recommendations:
        
        Price: {market_data.get('price', 'N/A')}
        24h Change: {market_data.get('change_24h', 'N/A')}
        Volume: {market_data.get('volume', 'N/A')}
        
        Provide:
        1. Market trend analysis
        2. Entry/exit recommendations
        3. Risk assessment
        """
        
        self.user_proxy.initiate_chat(self.assistant, message=message)
        
    async def execute_trade(self, task: dict):
        """Execute a trade"""
        # In production, this would connect to real exchanges
        trade_params = task.get("params", {})
        
        message = f"""Validate and execute the following trade:
        Symbol: {trade_params.get('symbol')}
        Side: {trade_params.get('side', 'buy')}
        Amount: {trade_params.get('amount')}
        Price: {trade_params.get('price', 'market')}
        
        Ensure proper risk management and position sizing."""
        
        self.user_proxy.initiate_chat(self.assistant, message=message)