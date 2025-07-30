from typing import Dict, Any, Callable, List, Tuple
import logging
from datetime import datetime, timedelta
import numpy as np
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from portfolio_optimizer import PortfolioOptimizer
from exchange_connector import ExchangeConnector

logger = logging.getLogger(__name__)


class PortfolioOptimizationAgent:
    """Portfolio optimization agent implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.optimization_method = config.get("optimization_method", "mean_variance")
        self.rebalance_frequency = config.get("rebalance_frequency", "weekly")
        self.risk_tolerance = config.get("risk_tolerance", "moderate")
        
        # Initialize portfolio optimizer
        self.optimizer = PortfolioOptimizer()
        
        # Initialize exchange connector for market data
        exchange_name = config.get("exchange", "binance")
        exchange_config = {
            'api_key': os.getenv(f'{exchange_name.upper()}_API_KEY', config.get('api_key')),
            'api_secret': os.getenv(f'{exchange_name.upper()}_API_SECRET', config.get('api_secret')),
            'testnet': config.get('testnet', True)
        }
        self.exchange = ExchangeConnector(exchange_name, exchange_config)
        self._initialized = False
        
    def get_system_message(self) -> str:
        """Get the system message for the portfolio optimization agent"""
        return f"""You are an expert portfolio optimization agent specializing in cryptocurrency portfolio management:

1. Portfolio Construction: Build optimal portfolios based on risk-return profiles
2. Asset Allocation: Determine optimal weights for each asset
3. Rebalancing: Execute periodic rebalancing to maintain target allocations
4. Performance Analysis: Track and analyze portfolio performance metrics
5. Risk Optimization: Minimize risk while maximizing returns

Optimization Method: {self.optimization_method}
Rebalance Frequency: {self.rebalance_frequency}
Risk Tolerance: {self.risk_tolerance}

Focus on building diversified portfolios that match the investor's risk profile.
Always consider correlation, volatility, and expected returns in optimization.
"""
    
    def get_functions(self) -> Dict[str, Callable]:
        """Get available functions for the portfolio optimization agent"""
        return {
            "optimize_portfolio": self.optimize_portfolio,
            "calculate_efficient_frontier": self.calculate_efficient_frontier,
            "rebalance_portfolio": self.rebalance_portfolio,
            "analyze_performance": self.analyze_performance,
            "calculate_sharpe_ratio": self.calculate_sharpe_ratio,
            "suggest_allocation": self.suggest_allocation,
            "backtest_strategy": self.backtest_strategy,
            "calculate_portfolio_metrics": self.calculate_portfolio_metrics
        }
    
    async def optimize_portfolio(self, assets: List[Dict[str, Any]], 
                                constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Optimize portfolio allocation using mean-variance optimization"""
        try:
            if constraints is None:
                constraints = {
                    "min_weight": 0.05,
                    "max_weight": 0.40,
                    "target_return": None
                }
            
            # Initialize exchange if needed
            if not self._initialized:
                await self.exchange.initialize()
                self._initialized = True
            
            # Get historical price data for optimization
            prices_history = {}
            for asset in assets:
                symbol = asset["symbol"]
                try:
                    market_data = await self.exchange.get_market_data(symbol, "1d", 90)
                    prices_history[symbol] = market_data["data"]["close"]
                except Exception as e:
                    logger.warning(f"Could not fetch data for {symbol}: {e}")
            
            # Use real portfolio optimizer if we have data
            if len(prices_history) >= 2:
                result = await self.optimizer.optimize_portfolio(
                    assets=assets,
                    prices_history=prices_history,
                    method=self.optimization_method,
                    constraints=constraints
                )
                
                # Add recommendations based on results
                recommendations = []
                if result["sharpe_ratio"] > 1.0:
                    recommendations.append("Portfolio has excellent risk-adjusted returns")
                elif result["sharpe_ratio"] > 0.5:
                    recommendations.append("Portfolio shows good risk-adjusted performance")
                else:
                    recommendations.append("Consider adjusting allocation for better risk-adjusted returns")
                
                if result["expected_volatility"] > 0.25:
                    recommendations.append("Portfolio has high volatility - consider adding stable assets")
                elif result["expected_volatility"] < 0.10:
                    recommendations.append("Portfolio is very conservative - consider growth assets for higher returns")
                
                result["recommendations"] = recommendations
                return result
            else:
                # Fallback to simple allocation if no data
                num_assets = len(assets)
                base_weight = 1.0 / num_assets
                weights = {}
                
                for asset in assets:
                    symbol = asset["symbol"]
                    if "BTC" in symbol:
                        weights[symbol] = min(0.35, base_weight * 1.5)
                    elif "ETH" in symbol:
                        weights[symbol] = min(0.25, base_weight * 1.2)
                    else:
                        weights[symbol] = max(0.05, base_weight * 0.8)
                
                total_weight = sum(weights.values())
                weights = {k: v/total_weight for k, v in weights.items()}
                
                return {
                    "optimal_weights": weights,
                    "expected_return": 0.125,
                    "expected_volatility": 0.18,
                    "sharpe_ratio": 0.69,
                    "optimization_method": "fallback",
                    "constraints_applied": constraints,
                    "recommendations": [
                        "Using simplified allocation due to insufficient market data",
                        "Connect to exchange API for real optimization"
                    ],
                    "mode": "simulated"
                }
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return {"error": str(e)}
    
    async def calculate_efficient_frontier(self, assets: List[Dict[str, Any]], 
                                         num_portfolios: int = 50) -> Dict[str, Any]:
        """Calculate efficient frontier for given assets"""
        try:
            # Generate mock efficient frontier data
            min_vol = 0.10
            max_vol = 0.35
            
            portfolios = []
            for i in range(num_portfolios):
                vol = min_vol + (max_vol - min_vol) * (i / num_portfolios)
                # Simple quadratic relationship for return
                ret = 0.05 + 0.8 * vol - 0.5 * vol**2
                
                portfolios.append({
                    "volatility": vol,
                    "return": ret,
                    "sharpe_ratio": ret / vol if vol > 0 else 0
                })
            
            # Find optimal portfolio (max Sharpe)
            optimal_idx = max(range(len(portfolios)), 
                            key=lambda i: portfolios[i]["sharpe_ratio"])
            
            return {
                "efficient_frontier": portfolios,
                "optimal_portfolio": portfolios[optimal_idx],
                "min_variance_portfolio": portfolios[0],
                "max_return_portfolio": portfolios[-1],
                "current_portfolio_position": {
                    "volatility": 0.18,
                    "return": 0.125,
                    "efficiency": "near_optimal"
                }
            }
        except Exception as e:
            logger.error(f"Error calculating efficient frontier: {e}")
            return {"error": str(e)}
    
    async def rebalance_portfolio(self, current_allocation: Dict[str, float],
                                 target_allocation: Dict[str, float],
                                 current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Calculate rebalancing trades needed"""
        try:
            total_value = sum(current_allocation.values())
            trades = []
            
            for symbol in set(current_allocation.keys()) | set(target_allocation.keys()):
                current_value = current_allocation.get(symbol, 0)
                target_value = target_allocation.get(symbol, 0) * total_value
                
                difference = target_value - current_value
                if abs(difference) > total_value * 0.01:  # 1% threshold
                    trades.append({
                        "symbol": symbol,
                        "action": "buy" if difference > 0 else "sell",
                        "amount": abs(difference) / current_prices.get(symbol, 1),
                        "value": abs(difference),
                        "current_weight": current_value / total_value,
                        "target_weight": target_allocation.get(symbol, 0)
                    })
            
            return {
                "rebalance_needed": len(trades) > 0,
                "trades": sorted(trades, key=lambda x: x["value"], reverse=True),
                "total_turnover": sum(t["value"] for t in trades),
                "turnover_percentage": sum(t["value"] for t in trades) / total_value * 100,
                "estimated_cost": sum(t["value"] for t in trades) * 0.001,  # 0.1% trading cost
                "rebalance_urgency": self._calculate_rebalance_urgency(current_allocation, target_allocation)
            }
        except Exception as e:
            logger.error(f"Error calculating rebalance: {e}")
            return {"error": str(e)}
    
    async def analyze_performance(self, portfolio_history: List[Dict[str, Any]],
                                 benchmark: str = "BTC") -> Dict[str, Any]:
        """Analyze portfolio performance metrics"""
        try:
            # Mock performance analysis
            returns = [0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.02, -0.01, 0.03, 0.01]
            
            cumulative_return = np.prod([1 + r for r in returns]) - 1
            avg_return = np.mean(returns)
            volatility = np.std(returns)
            
            # Mock benchmark comparison
            benchmark_return = 0.15
            alpha = cumulative_return - benchmark_return
            
            return {
                "period": f"{len(returns)} periods",
                "total_return": cumulative_return,
                "annualized_return": (1 + cumulative_return) ** (252/len(returns)) - 1,
                "volatility": volatility * np.sqrt(252),
                "sharpe_ratio": (avg_return / volatility) * np.sqrt(252) if volatility > 0 else 0,
                "max_drawdown": 0.12,  # Mock 12% max drawdown
                "win_rate": len([r for r in returns if r > 0]) / len(returns),
                "benchmark_comparison": {
                    "benchmark": benchmark,
                    "benchmark_return": benchmark_return,
                    "alpha": alpha,
                    "tracking_error": 0.08,
                    "information_ratio": alpha / 0.08
                },
                "risk_adjusted_metrics": {
                    "sortino_ratio": 1.2,
                    "calmar_ratio": 1.0,
                    "omega_ratio": 1.5
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return {"error": str(e)}
    
    def calculate_sharpe_ratio(self, returns: List[float], 
                              risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """Calculate Sharpe ratio for given returns"""
        try:
            returns_array = np.array(returns)
            
            avg_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            
            # Annualize (assuming daily returns)
            annual_return = (1 + avg_return) ** 252 - 1
            annual_std = std_return * np.sqrt(252)
            
            sharpe_ratio = (annual_return - risk_free_rate) / annual_std if annual_std > 0 else 0
            
            return {
                "sharpe_ratio": sharpe_ratio,
                "annual_return": annual_return,
                "annual_volatility": annual_std,
                "risk_free_rate": risk_free_rate,
                "interpretation": self._interpret_sharpe(sharpe_ratio)
            }
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return {"error": str(e)}
    
    async def suggest_allocation(self, risk_profile: str, 
                               market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest portfolio allocation based on risk profile"""
        try:
            # Base allocations by risk profile
            allocations = {
                "conservative": {
                    "BTC/USDT": 0.40,
                    "ETH/USDT": 0.30,
                    "USDT/USDT": 0.20,
                    "USDC/USDT": 0.10
                },
                "moderate": {
                    "BTC/USDT": 0.35,
                    "ETH/USDT": 0.25,
                    "SOL/USDT": 0.15,
                    "MATIC/USDT": 0.10,
                    "LINK/USDT": 0.10,
                    "USDT/USDT": 0.05
                },
                "aggressive": {
                    "BTC/USDT": 0.25,
                    "ETH/USDT": 0.20,
                    "SOL/USDT": 0.15,
                    "AVAX/USDT": 0.10,
                    "DOT/USDT": 0.10,
                    "NEAR/USDT": 0.10,
                    "INJ/USDT": 0.10
                }
            }
            
            suggested = allocations.get(risk_profile, allocations["moderate"])
            
            # Adjust based on market conditions
            if market_conditions.get("trend") == "bearish":
                # Increase stablecoin allocation
                if "USDT/USDT" in suggested:
                    suggested["USDT/USDT"] *= 1.5
                else:
                    suggested["USDT/USDT"] = 0.10
                
                # Normalize weights
                total = sum(suggested.values())
                suggested = {k: v/total for k, v in suggested.items()}
            
            return {
                "risk_profile": risk_profile,
                "suggested_allocation": suggested,
                "expected_metrics": {
                    "annual_return": self._get_expected_return(risk_profile),
                    "annual_volatility": self._get_expected_volatility(risk_profile),
                    "max_drawdown": self._get_expected_drawdown(risk_profile)
                },
                "rationale": self._get_allocation_rationale(risk_profile, market_conditions),
                "rebalance_frequency": self._get_rebalance_frequency(risk_profile)
            }
        except Exception as e:
            logger.error(f"Error suggesting allocation: {e}")
            return {"error": str(e)}
    
    async def backtest_strategy(self, strategy: Dict[str, Any], 
                               historical_data: Dict[str, List[float]],
                               initial_capital: float = 10000) -> Dict[str, Any]:
        """Backtest a portfolio strategy"""
        try:
            # Simplified backtest
            num_periods = min(len(prices) for prices in historical_data.values())
            portfolio_values = [initial_capital]
            
            # Initial allocation
            weights = strategy.get("weights", {k: 1/len(historical_data) for k in historical_data})
            positions = {symbol: initial_capital * weight / historical_data[symbol][0] 
                        for symbol, weight in weights.items()}
            
            # Simulate portfolio over time
            for i in range(1, num_periods):
                portfolio_value = sum(positions[symbol] * historical_data[symbol][i] 
                                    for symbol in positions)
                portfolio_values.append(portfolio_value)
                
                # Rebalance if needed (monthly)
                if i % 30 == 0:
                    for symbol in positions:
                        positions[symbol] = portfolio_value * weights[symbol] / historical_data[symbol][i]
            
            # Calculate metrics
            returns = [(portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1] 
                      for i in range(1, len(portfolio_values))]
            
            total_return = (portfolio_values[-1] - initial_capital) / initial_capital
            sharpe = self.calculate_sharpe_ratio(returns)["sharpe_ratio"]
            
            return {
                "initial_capital": initial_capital,
                "final_value": portfolio_values[-1],
                "total_return": total_return,
                "annualized_return": (1 + total_return) ** (252/num_periods) - 1,
                "sharpe_ratio": sharpe,
                "max_drawdown": self._calculate_max_drawdown(portfolio_values),
                "win_rate": len([r for r in returns if r > 0]) / len(returns),
                "best_period": max(returns),
                "worst_period": min(returns),
                "num_rebalances": num_periods // 30
            }
        except Exception as e:
            logger.error(f"Error backtesting strategy: {e}")
            return {"error": str(e)}
    
    async def calculate_portfolio_metrics(self, holdings: Dict[str, float],
                                        prices: Dict[str, float]) -> Dict[str, Any]:
        """Calculate comprehensive portfolio metrics"""
        try:
            # Calculate values and weights
            values = {symbol: amount * prices[symbol] for symbol, amount in holdings.items()}
            total_value = sum(values.values())
            weights = {symbol: value / total_value for symbol, value in values.items()}
            
            # Concentration metrics
            herfindahl_index = sum(w**2 for w in weights.values())
            effective_assets = 1 / herfindahl_index if herfindahl_index > 0 else 0
            
            # Risk metrics (mock)
            portfolio_beta = sum(weights.get(s, 0) * self._get_asset_beta(s) for s in weights)
            
            return {
                "total_value": total_value,
                "holdings": holdings,
                "weights": weights,
                "concentration_metrics": {
                    "herfindahl_index": herfindahl_index,
                    "effective_assets": effective_assets,
                    "largest_position": max(weights.values()),
                    "top_3_concentration": sum(sorted(weights.values(), reverse=True)[:3])
                },
                "risk_metrics": {
                    "portfolio_beta": portfolio_beta,
                    "diversification_ratio": 1 / herfindahl_index if herfindahl_index > 0 else 0,
                    "correlation_risk": self._estimate_correlation_risk(list(weights.keys()))
                },
                "allocation_quality": {
                    "balance_score": self._calculate_balance_score(weights),
                    "risk_adjusted_score": self._calculate_risk_adjusted_score(weights),
                    "efficiency_score": self._calculate_efficiency_score(weights)
                }
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {"error": str(e)}
    
    # Helper methods
    def _calculate_rebalance_urgency(self, current: Dict[str, float], 
                                    target: Dict[str, float]) -> str:
        total_current = sum(current.values())
        max_deviation = 0
        
        for symbol in set(current.keys()) | set(target.keys()):
            current_weight = current.get(symbol, 0) / total_current if total_current > 0 else 0
            target_weight = target.get(symbol, 0)
            deviation = abs(current_weight - target_weight)
            max_deviation = max(max_deviation, deviation)
        
        if max_deviation > 0.10:
            return "high"
        elif max_deviation > 0.05:
            return "medium"
        else:
            return "low"
    
    def _interpret_sharpe(self, sharpe: float) -> str:
        if sharpe < 0:
            return "Poor - negative risk-adjusted returns"
        elif sharpe < 0.5:
            return "Below average - low risk-adjusted returns"
        elif sharpe < 1.0:
            return "Average - acceptable risk-adjusted returns"
        elif sharpe < 2.0:
            return "Good - strong risk-adjusted returns"
        else:
            return "Excellent - exceptional risk-adjusted returns"
    
    def _get_expected_return(self, risk_profile: str) -> float:
        returns = {
            "conservative": 0.08,
            "moderate": 0.12,
            "aggressive": 0.18
        }
        return returns.get(risk_profile, 0.12)
    
    def _get_expected_volatility(self, risk_profile: str) -> float:
        volatility = {
            "conservative": 0.12,
            "moderate": 0.18,
            "aggressive": 0.25
        }
        return volatility.get(risk_profile, 0.18)
    
    def _get_expected_drawdown(self, risk_profile: str) -> float:
        drawdowns = {
            "conservative": 0.15,
            "moderate": 0.25,
            "aggressive": 0.35
        }
        return drawdowns.get(risk_profile, 0.25)
    
    def _get_allocation_rationale(self, risk_profile: str, 
                                 market_conditions: Dict[str, Any]) -> List[str]:
        rationale = []
        
        if risk_profile == "conservative":
            rationale.append("Focus on established cryptocurrencies with lower volatility")
            rationale.append("Significant stablecoin allocation for capital preservation")
        elif risk_profile == "aggressive":
            rationale.append("Diversified across high-growth potential altcoins")
            rationale.append("Minimal stablecoin allocation to maximize growth")
        
        if market_conditions.get("trend") == "bullish":
            rationale.append("Market conditions favor risk-on positioning")
        elif market_conditions.get("trend") == "bearish":
            rationale.append("Defensive positioning due to bearish market conditions")
        
        return rationale
    
    def _get_rebalance_frequency(self, risk_profile: str) -> str:
        frequencies = {
            "conservative": "monthly",
            "moderate": "bi-weekly",
            "aggressive": "weekly"
        }
        return frequencies.get(risk_profile, "bi-weekly")
    
    def _calculate_max_drawdown(self, values: List[float]) -> float:
        peak = values[0]
        max_dd = 0
        
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _get_asset_beta(self, symbol: str) -> float:
        # Mock beta values
        betas = {
            "BTC/USDT": 1.0,
            "ETH/USDT": 1.2,
            "SOL/USDT": 1.5,
            "MATIC/USDT": 1.4,
            "USDT/USDT": 0.0,
            "USDC/USDT": 0.0
        }
        return betas.get(symbol, 1.3)
    
    def _estimate_correlation_risk(self, symbols: List[str]) -> float:
        # Simplified correlation risk estimate
        if len(symbols) <= 2:
            return 0.9
        elif len(symbols) <= 5:
            return 0.7
        else:
            return 0.5
    
    def _calculate_balance_score(self, weights: Dict[str, float]) -> float:
        # Score based on how evenly distributed the portfolio is
        ideal_weight = 1 / len(weights)
        deviations = [abs(w - ideal_weight) for w in weights.values()]
        return 1 - (sum(deviations) / len(deviations)) / ideal_weight
    
    def _calculate_risk_adjusted_score(self, weights: Dict[str, float]) -> float:
        # Mock risk-adjusted score
        return 0.75
    
    def _calculate_efficiency_score(self, weights: Dict[str, float]) -> float:
        # Mock efficiency score
        return 0.82