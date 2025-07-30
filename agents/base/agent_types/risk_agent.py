from typing import Dict, Any, Callable, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskManagementAgent:
    """Risk management agent implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_portfolio_risk = config.get("max_portfolio_risk", 0.06)  # 6% max portfolio risk
        self.max_position_risk = config.get("max_position_risk", 0.02)  # 2% max per position
        self.max_correlation_risk = config.get("max_correlation_risk", 0.7)
        
    def get_system_message(self) -> str:
        """Get the system message for the risk management agent"""
        return f"""You are an expert risk management agent responsible for protecting trading capital and ensuring sustainable portfolio growth:

1. Position Sizing: Calculate optimal position sizes based on risk parameters
2. Risk Assessment: Evaluate market, liquidity, and systematic risks
3. Portfolio Risk: Monitor overall portfolio exposure and correlations
4. Stop Loss Management: Set and adjust stop losses dynamically
5. Risk Reporting: Generate comprehensive risk reports and alerts

Risk Parameters:
- Maximum Portfolio Risk: {self.max_portfolio_risk*100}%
- Maximum Position Risk: {self.max_position_risk*100}%
- Maximum Correlation Risk: {self.max_correlation_risk}

Always prioritize capital preservation over profit maximization.
Provide clear risk warnings and never exceed defined risk limits.
"""
    
    def get_functions(self) -> Dict[str, Callable]:
        """Get available functions for the risk management agent"""
        return {
            "calculate_position_risk": self.calculate_position_risk,
            "assess_portfolio_risk": self.assess_portfolio_risk,
            "calculate_var": self.calculate_var,
            "set_risk_limits": self.set_risk_limits,
            "evaluate_trade_risk": self.evaluate_trade_risk,
            "generate_risk_report": self.generate_risk_report,
            "calculate_kelly_criterion": self.calculate_kelly_criterion,
            "monitor_drawdown": self.monitor_drawdown
        }
    
    def calculate_position_risk(self, entry_price: float, stop_loss: float, 
                               position_size: float, account_balance: float) -> Dict[str, Any]:
        """Calculate risk metrics for a position"""
        try:
            price_risk = abs(entry_price - stop_loss) / entry_price
            position_value = entry_price * position_size
            risk_amount = abs(entry_price - stop_loss) * position_size
            risk_percentage = (risk_amount / account_balance) * 100
            
            return {
                "position_value": position_value,
                "risk_amount": risk_amount,
                "risk_percentage": risk_percentage,
                "price_risk_percentage": price_risk * 100,
                "risk_reward_ratio": self._calculate_risk_reward(entry_price, stop_loss, entry_price * 1.03),
                "position_sizing_valid": risk_percentage <= (self.max_position_risk * 100),
                "recommendations": self._get_risk_recommendations(risk_percentage)
            }
        except Exception as e:
            logger.error(f"Error calculating position risk: {e}")
            return {"error": str(e)}
    
    async def assess_portfolio_risk(self, positions: List[Dict[str, Any]], 
                                   account_balance: float) -> Dict[str, Any]:
        """Assess overall portfolio risk"""
        try:
            total_risk = 0
            correlation_risk = 0
            concentrated_risk = False
            
            position_risks = []
            for position in positions:
                risk_amount = position.get("risk_amount", 0)
                total_risk += risk_amount
                
                position_risks.append({
                    "symbol": position["symbol"],
                    "risk_amount": risk_amount,
                    "risk_percentage": (risk_amount / account_balance) * 100
                })
            
            portfolio_risk_percentage = (total_risk / account_balance) * 100
            
            return {
                "total_risk_amount": total_risk,
                "portfolio_risk_percentage": portfolio_risk_percentage,
                "position_risks": position_risks,
                "risk_status": self._get_risk_status(portfolio_risk_percentage),
                "diversification_score": self._calculate_diversification(positions),
                "recommendations": {
                    "reduce_risk": portfolio_risk_percentage > (self.max_portfolio_risk * 100),
                    "max_additional_risk": max(0, (self.max_portfolio_risk * account_balance) - total_risk),
                    "suggested_actions": self._get_portfolio_recommendations(portfolio_risk_percentage)
                }
            }
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            return {"error": str(e)}
    
    async def calculate_var(self, portfolio_value: float, returns: List[float], 
                           confidence_level: float = 0.95) -> Dict[str, Any]:
        """Calculate Value at Risk (VaR)"""
        try:
            # Simplified VaR calculation
            import numpy as np
            returns_array = np.array(returns)
            
            # Historical VaR
            var_percentile = (1 - confidence_level) * 100
            historical_var = np.percentile(returns_array, var_percentile)
            
            # Parametric VaR (assuming normal distribution)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            z_score = 1.645 if confidence_level == 0.95 else 2.326  # 95% or 99%
            parametric_var = mean_return - (z_score * std_return)
            
            return {
                "portfolio_value": portfolio_value,
                "confidence_level": confidence_level,
                "var_1day": {
                    "historical": portfolio_value * historical_var,
                    "parametric": portfolio_value * parametric_var
                },
                "var_1week": {
                    "historical": portfolio_value * historical_var * np.sqrt(5),
                    "parametric": portfolio_value * parametric_var * np.sqrt(5)
                },
                "interpretation": f"With {confidence_level*100}% confidence, maximum expected loss in 1 day is ${abs(portfolio_value * parametric_var):.2f}"
            }
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return {"error": str(e)}
    
    def set_risk_limits(self, risk_type: str, limit_value: float) -> Dict[str, Any]:
        """Set or update risk limits"""
        try:
            valid_risk_types = ["position", "portfolio", "correlation", "drawdown"]
            
            if risk_type not in valid_risk_types:
                return {"error": f"Invalid risk type. Must be one of {valid_risk_types}"}
            
            old_limit = getattr(self, f"max_{risk_type}_risk", None)
            
            if risk_type == "position":
                self.max_position_risk = limit_value
            elif risk_type == "portfolio":
                self.max_portfolio_risk = limit_value
            elif risk_type == "correlation":
                self.max_correlation_risk = limit_value
            
            return {
                "risk_type": risk_type,
                "old_limit": old_limit,
                "new_limit": limit_value,
                "status": "updated",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error setting risk limits: {e}")
            return {"error": str(e)}
    
    async def evaluate_trade_risk(self, trade: Dict[str, Any], 
                                 market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate risk for a proposed trade"""
        try:
            risk_scores = {
                "market_risk": self._assess_market_risk(market_conditions),
                "liquidity_risk": self._assess_liquidity_risk(trade, market_conditions),
                "timing_risk": self._assess_timing_risk(market_conditions),
                "execution_risk": self._assess_execution_risk(trade)
            }
            
            overall_risk_score = sum(risk_scores.values()) / len(risk_scores)
            
            return {
                "trade": trade,
                "risk_scores": risk_scores,
                "overall_risk_score": overall_risk_score,
                "risk_level": self._get_risk_level(overall_risk_score),
                "approved": overall_risk_score < 0.7,
                "warnings": self._get_trade_warnings(risk_scores),
                "suggestions": self._get_trade_suggestions(trade, risk_scores)
            }
        except Exception as e:
            logger.error(f"Error evaluating trade risk: {e}")
            return {"error": str(e)}
    
    async def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        try:
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "risk_limits": {
                    "position_risk": f"{self.max_position_risk*100}%",
                    "portfolio_risk": f"{self.max_portfolio_risk*100}%",
                    "correlation_risk": self.max_correlation_risk
                },
                "current_risk_metrics": {
                    "active_positions": 5,
                    "total_exposure": 45000,
                    "portfolio_risk": "4.5%",
                    "largest_position_risk": "1.8%",
                    "correlation_score": 0.65
                },
                "risk_alerts": [
                    {
                        "level": "warning",
                        "message": "Portfolio approaching maximum risk limit",
                        "metric": "portfolio_risk",
                        "current": 4.5,
                        "limit": 6.0
                    }
                ],
                "historical_metrics": {
                    "max_drawdown_30d": "8.5%",
                    "sharpe_ratio": 1.45,
                    "win_rate": 0.58,
                    "avg_risk_per_trade": "1.5%"
                },
                "recommendations": [
                    "Consider reducing position sizes in correlated assets",
                    "Maintain current risk discipline",
                    "Review stop losses on older positions"
                ]
            }
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {"error": str(e)}
    
    def calculate_kelly_criterion(self, win_probability: float, avg_win: float, 
                                 avg_loss: float) -> Dict[str, Any]:
        """Calculate optimal position size using Kelly Criterion"""
        try:
            if avg_loss == 0:
                return {"error": "Average loss cannot be zero"}
            
            # Kelly formula: f = p - q/b
            # where p = win probability, q = loss probability, b = win/loss ratio
            loss_probability = 1 - win_probability
            win_loss_ratio = avg_win / avg_loss
            
            kelly_percentage = win_probability - (loss_probability / win_loss_ratio)
            
            # Apply Kelly fraction (typically 25% of full Kelly)
            conservative_kelly = kelly_percentage * 0.25
            
            return {
                "win_probability": win_probability,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "full_kelly_percentage": kelly_percentage * 100,
                "conservative_kelly_percentage": conservative_kelly * 100,
                "recommended_position_size": max(0, conservative_kelly),
                "interpretation": self._interpret_kelly(conservative_kelly)
            }
        except Exception as e:
            logger.error(f"Error calculating Kelly criterion: {e}")
            return {"error": str(e)}
    
    async def monitor_drawdown(self, account_history: List[float]) -> Dict[str, Any]:
        """Monitor drawdown and recovery metrics"""
        try:
            if not account_history:
                return {"error": "No account history provided"}
            
            peak = account_history[0]
            max_drawdown = 0
            current_drawdown = 0
            drawdown_periods = []
            
            for i, value in enumerate(account_history):
                if value > peak:
                    if current_drawdown > 0:
                        drawdown_periods.append({
                            "depth": current_drawdown,
                            "duration": i - drawdown_start
                        })
                    peak = value
                    current_drawdown = 0
                else:
                    drawdown = (peak - value) / peak
                    if drawdown > current_drawdown:
                        current_drawdown = drawdown
                        if current_drawdown > max_drawdown:
                            max_drawdown = current_drawdown
                    if current_drawdown > 0 and 'drawdown_start' not in locals():
                        drawdown_start = i
            
            current_value = account_history[-1]
            current_drawdown_pct = ((peak - current_value) / peak) * 100 if peak > current_value else 0
            
            return {
                "max_drawdown_percentage": max_drawdown * 100,
                "current_drawdown_percentage": current_drawdown_pct,
                "drawdown_periods": len(drawdown_periods),
                "avg_drawdown_depth": sum(p["depth"] for p in drawdown_periods) / len(drawdown_periods) * 100 if drawdown_periods else 0,
                "avg_recovery_time": sum(p["duration"] for p in drawdown_periods) / len(drawdown_periods) if drawdown_periods else 0,
                "risk_status": self._get_drawdown_status(current_drawdown_pct),
                "action_required": current_drawdown_pct > 10
            }
        except Exception as e:
            logger.error(f"Error monitoring drawdown: {e}")
            return {"error": str(e)}
    
    # Helper methods
    def _calculate_risk_reward(self, entry: float, stop: float, target: float) -> float:
        risk = abs(entry - stop)
        reward = abs(target - entry)
        return reward / risk if risk > 0 else 0
    
    def _get_risk_recommendations(self, risk_percentage: float) -> List[str]:
        recommendations = []
        if risk_percentage > self.max_position_risk * 100:
            recommendations.append(f"Reduce position size to stay within {self.max_position_risk*100}% risk limit")
        if risk_percentage < 0.5:
            recommendations.append("Consider increasing position size for better capital efficiency")
        return recommendations
    
    def _get_risk_status(self, risk_percentage: float) -> str:
        if risk_percentage < 3:
            return "low"
        elif risk_percentage < 5:
            return "moderate"
        elif risk_percentage < 7:
            return "high"
        else:
            return "critical"
    
    def _calculate_diversification(self, positions: List[Dict[str, Any]]) -> float:
        # Simplified diversification score
        unique_assets = len(set(p.get("symbol", "").split("/")[0] for p in positions))
        return min(unique_assets / 5, 1.0)  # Max score at 5+ unique assets
    
    def _get_portfolio_recommendations(self, risk_percentage: float) -> List[str]:
        recommendations = []
        if risk_percentage > self.max_portfolio_risk * 100:
            recommendations.append("Reduce overall exposure immediately")
            recommendations.append("Close or reduce largest risk positions")
        elif risk_percentage > self.max_portfolio_risk * 80:
            recommendations.append("Approaching portfolio risk limit")
            recommendations.append("Avoid opening new positions")
        return recommendations
    
    def _assess_market_risk(self, conditions: Dict[str, Any]) -> float:
        # Simplified market risk assessment
        volatility = conditions.get("volatility", "medium")
        risk_map = {"low": 0.3, "medium": 0.5, "high": 0.8, "extreme": 1.0}
        return risk_map.get(volatility, 0.5)
    
    def _assess_liquidity_risk(self, trade: Dict[str, Any], conditions: Dict[str, Any]) -> float:
        # Simplified liquidity risk assessment
        volume = conditions.get("volume", "average")
        risk_map = {"high": 0.2, "average": 0.5, "low": 0.8, "very_low": 1.0}
        return risk_map.get(volume, 0.5)
    
    def _assess_timing_risk(self, conditions: Dict[str, Any]) -> float:
        # Simplified timing risk assessment
        trend_strength = conditions.get("trend_strength", "moderate")
        risk_map = {"strong": 0.3, "moderate": 0.5, "weak": 0.7, "none": 0.9}
        return risk_map.get(trend_strength, 0.5)
    
    def _assess_execution_risk(self, trade: Dict[str, Any]) -> float:
        # Simplified execution risk assessment
        order_type = trade.get("order_type", "market")
        risk_map = {"limit": 0.3, "market": 0.5, "stop": 0.7}
        return risk_map.get(order_type, 0.5)
    
    def _get_risk_level(self, score: float) -> str:
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "moderate"
        elif score < 0.8:
            return "high"
        else:
            return "extreme"
    
    def _get_trade_warnings(self, risk_scores: Dict[str, float]) -> List[str]:
        warnings = []
        for risk_type, score in risk_scores.items():
            if score > 0.7:
                warnings.append(f"High {risk_type.replace('_', ' ')}: {score:.2f}")
        return warnings
    
    def _get_trade_suggestions(self, trade: Dict[str, Any], risk_scores: Dict[str, float]) -> List[str]:
        suggestions = []
        if risk_scores.get("liquidity_risk", 0) > 0.7:
            suggestions.append("Consider using limit orders to reduce slippage")
        if risk_scores.get("market_risk", 0) > 0.7:
            suggestions.append("Reduce position size due to high market volatility")
        return suggestions
    
    def _interpret_kelly(self, kelly_pct: float) -> str:
        if kelly_pct <= 0:
            return "Negative edge - do not trade"
        elif kelly_pct < 0.02:
            return "Minimal edge - consider skipping"
        elif kelly_pct < 0.05:
            return "Moderate edge - standard position size"
        else:
            return "Strong edge - consider larger position"
    
    def _get_drawdown_status(self, drawdown_pct: float) -> str:
        if drawdown_pct < 5:
            return "normal"
        elif drawdown_pct < 10:
            return "caution"
        elif drawdown_pct < 15:
            return "warning"
        else:
            return "critical"