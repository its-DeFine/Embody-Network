"""Analysis Agent Implementation"""
from .base_agent import BaseAgent

class AnalysisAgent(BaseAgent):
    """Agent for market analysis and research"""
    
    def get_system_message(self) -> str:
        return """You are a financial analysis expert specializing in market research and technical analysis.
        Your responsibilities include:
        - Performing comprehensive market analysis
        - Identifying trends and patterns
        - Generating detailed reports
        - Providing actionable insights
        
        Use technical indicators, fundamental analysis, and market sentiment in your analysis."""
    
    async def handle_task(self, task: dict):
        """Handle analysis-specific tasks"""
        task_type = task.get("type")
        
        if task_type == "technical_analysis":
            await self.technical_analysis(task)
            
        elif task_type == "market_report":
            await self.generate_market_report(task)
            
        else:
            await super().handle_task(task)
    
    async def technical_analysis(self, task: dict):
        """Perform technical analysis"""
        symbol = task.get("symbol", "BTC/USD")
        indicators = task.get("indicators", ["RSI", "MACD", "MA"])
        
        market_data = await self.get_market_data(symbol)
        
        message = f"""Perform technical analysis for {symbol} using the following indicators: {', '.join(indicators)}
        
        Current market data:
        Price: {market_data.get('price', 'N/A')}
        Volume: {market_data.get('volume', 'N/A')}
        
        Provide:
        1. Indicator values and interpretation
        2. Support and resistance levels
        3. Trend direction and strength
        4. Trading signals
        """
        
        self.user_proxy.initiate_chat(self.assistant, message=message)
    
    async def generate_market_report(self, task: dict):
        """Generate comprehensive market report"""
        symbols = task.get("symbols", ["BTC/USD", "ETH/USD"])
        
        message = f"""Generate a comprehensive market report for the following assets: {', '.join(symbols)}
        
        Include:
        1. Market overview and trends
        2. Key price levels and targets
        3. Volume analysis
        4. Risk factors and opportunities
        5. Short-term and long-term outlook
        """
        
        self.user_proxy.initiate_chat(self.assistant, message=message)